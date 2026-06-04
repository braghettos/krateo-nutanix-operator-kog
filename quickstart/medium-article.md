# Creating Nutanix VMs the GitOps Way

### A Krateo operator for Prism Central v4 — and the little middleware that made it work

*How we turned a Nutanix OpenAPI spec into a Kubernetes operator with zero custom controller code, hit a wall, and got a VM to appear in Prism Central from a single `kubectl apply`.*

---

## A managed datacenter that feels like a cloud

For a decade, the gold standard of developer experience has been the public cloud: you ask for a resource, you get it in seconds, and you never file a ticket. The hard question for everyone running a **managed datacenter** — a private or hybrid estate — is how to deliver that same *self-service* experience on infrastructure you actually own, **without** handing developers the keys to production or drowning the platform team in requests.

The answer has two halves, and Krateo and Nutanix supply one each.

**Nutanix is the fully API-driven infrastructure.** Modern Nutanix is a software-defined datacenter where *every* primitive — virtual machines, subnets and VPCs, storage containers and volume groups, data protection, IAM — is exposed through the **Prism Central v4 REST API**. There's no resource you can click that you can't also `POST`. That matters because self-service is only as good as the API underneath it: if the datacenter is fully programmable, it can be fully automated, and anything that can be automated can be offered as a product.

**Krateo is the platform layer that turns those APIs into a product.** Krateo is an open-source **Cloud Management Platform** and **Internal Developer Portal**, built on Kubernetes. It does two jobs at once:

- As an **Internal Developer Portal**, it gives developers a catalog of *golden paths* — "I need a VM," "I need a network," "I need a dev environment" — through a self-service UI and Git, with templates, forms, and approvals. Developers describe *what* they want; they never touch the *how*.
- As a **Cloud Management Platform**, it gives platform teams the control plane: composable blueprints, GitOps reconciliation, RBAC, multi-tenancy, policy, and drift detection — so every self-service request lands inside the guardrails the organization defined.

Put them together and the picture is clean: **Nutanix provides the API-driven substrate, Krateo provides the self-service experience and the governance on top.** The managed datacenter starts to behave like a cloud — a developer portal at the front, a cloud management platform orchestrating in the middle, and a fully programmable Nutanix estate underneath. Private infrastructure, public-cloud ergonomics.

But there's a bridge to build between those two halves: Nutanix's API has to become *Kubernetes-native* — every resource a declarative object that Krateo can compose, template, and reconcile. That bridge is exactly what the rest of this article builds. The virtual machine is our first crossing.

---

If you live in Kubernetes, you want everything to look like a Kubernetes resource: declare the desired state in YAML, commit it, and let a controller reconcile reality. Infrastructure outside the cluster — VMs, networks, storage — should be no different.

Nutanix ships a clean, fully-documented **v4 REST API** for Prism Central. Krateo ships **KOG** (the *oasgen-provider*), which turns an OpenAPI spec into a Kubernetes CRD **and** a controller — no Go, no SDK, no custom reconciler. On paper, the two are a perfect match: point KOG at the Nutanix spec and you get an operator.

This is the story of doing exactly that for **virtual machines** — including the part where the generic operator couldn't quite speak Nutanix's dialect, and the 200-line proxy that fixed it for *every* Nutanix resource at once.

---

## The idea: an operator with no operator code

Krateo's KOG works from a single custom resource, the **`RestDefinition`**. You hand it an OpenAPI slice for one resource and a few hints (the verbs, the identifier), and it generates:

- a **CRD** for the resource (here, `Vm` in the `vmm.nutanix.krateo.io` group),
- a **`VmConfiguration`** CRD that holds the endpoint + auth,
- and a running **controller** (`rest-dynamic-controller`) that maps the CRD's verbs onto the REST API.

The `RestDefinition` for a Nutanix VM is almost boring:

```yaml
apiVersion: ogen.krateo.io/v1alpha1
kind: RestDefinition
metadata:
  name: nutanix-vmm-vm
  namespace: nutanix-system
spec:
  oasPath: configmap://nutanix-system/nutanix-vmm-vm-oas/vm.yaml
  resourceGroup: vmm.nutanix.krateo.io
  resource:
    kind: Vm
    identifiers:
      - name
    additionalStatusFields:
      - extId
    verbsDescription:
      - action: findby
        method: GET
        path: /vmm/v4.0/ahv/config/vms
      - action: create
        method: POST
        path: /vmm/v4.0/ahv/config/vms
      - action: get
        method: GET
        path: /vmm/v4.0/ahv/config/vms/{extId}
      - action: update
        method: PUT
        path: /vmm/v4.0/ahv/config/vms/{extId}
      - action: delete
        method: DELETE
        path: /vmm/v4.0/ahv/config/vms/{extId}
```

Apply it, and a `Vm` CRD and its controller appear. Now the end state we *want* is just this:

```yaml
apiVersion: vmm.nutanix.krateo.io/v1alpha1
kind: Vm
metadata:
  name: quickstart-vm
  namespace: nutanix-system
spec:
  configurationRef:
    name: nutanix-pc
    namespace: nutanix-system
  name: quickstart-vm
  numSockets: 1
  numCoresPerSocket: 1
  memorySizeBytes: 2147483648        # 2 GiB
  cluster:
    extId: "<your-prism-element-cluster>"
```

`kubectl apply -f vm.yaml`, and a VM should show up in Prism Central. That was the goal.

---

## The wall: a generic client meets an opinionated API

The first run didn't create a VM. The controller logged the same line, over and over:

```
ERROR  Cannot observe external resource   err="invalid response code: 4XX"
```

Here's the thing: a *generic* OpenAPI-driven controller assumes a fairly vanilla REST API. Nutanix v4 is excellent, but it has **five conventions** a generic client doesn't know about:

1. **A `$objectType` discriminator** must be present in every create/update body (e.g. `vmm.v4.ahv.config.Vm`). Miss it and you get a `500`.
2. **An `NTNX-Request-Id` header** — a fresh UUID per mutating call — is required for idempotency.
3. **Creates are asynchronous.** `POST` returns `202` and a *task reference*; the real resource only exists once you poll `/prism/v4.0/config/tasks/{id}` to `SUCCEEDED`.
4. **ETag / `If-Match`** optimistic concurrency on update and delete.
5. **OData `$filter`** for lookups — and the string value has to be quoted (`name eq 'x'`, not `name eq x`).

None of these can be expressed by the OpenAPI document alone, and the controller doesn't synthesize them. Worse, the *misleading* `4XX` turned out to be something else entirely: the generated OpenAPI slice declared its responses as **ranges** (`4XX`, `5XX`) instead of explicit codes — and `rest-dynamic-controller` couldn't match a real `200` against a range, so it rejected even successful responses.

Two different problems, then: **runtime protocol** (the five conventions) and **static codegen** (the response codes, plus a couple of over-strict required headers).

---

## The fix: a tiny translating proxy

The codegen issues are just edits to the OpenAPI slice (expand the range codes to `200/400/404/500`, stop marking `NTNX-Request-Id`/`If-Match` as *required*, expose `name` as a findby filter). Those belong upstream in the generator.

The runtime conventions are different — they're *behavior*, not schema. So we put a small, stdlib-only **reverse proxy** between the controller and Prism Central. The controller still thinks it's talking to a plain REST API; the proxy quietly does the Nutanix-specific work:

```
 kubectl ──▶ Vm CR ──▶ rest-dynamic-controller ──▶  [ Nutanix v4 proxy ]  ──▶ Prism Central
                          (generic HTTP)             quote $filter, inject
                                                     $objectType + Request-Id,
                                                     resolve async tasks,
                                                     add If-Match ETag
```

The whole adapter is five translations:

| # | The proxy does… | …so the controller doesn't have to |
|---|---|---|
| 1 | quote OData `$filter` values; turn `?name=X` into `name eq 'X'` | build OData |
| 2 | inject `$objectType` into bodies | know Nutanix's discriminator |
| 3 | add a fresh `NTNX-Request-Id` UUID | manage idempotency |
| 4 | poll `202 → task → SUCCEEDED` and return the **real resource** as `200` | understand async tasks |
| 5 | `GET` for the ETag, add `If-Match` on writes | do concurrency control |

The clever bit is translation #2. Hardcoding a `$objectType` per resource would defeat the purpose — Nutanix has hundreds of them. Instead the proxy **derives it from the request path**:

```
/vmm/v4.0/ahv/config/vms                         → vmm.v4.ahv.config.Vm
/prism/v4.0/config/categories                    → prism.v4.config.Category
/clustermgmt/v4.0/.../{id}/storage-containers    → clustermgmt.v4.config.StorageContainer
/storage/v4.0.a3/config/volume-groups            → storage.v4.r0.a3.config.VolumeGroup
```

Singularize and PascalCase the collection, normalize the version (GA `v4.0`→`v4`, alpha `v4.0.a3`→`v4.r0.a3`), strip parent `collection/{id}` pairs — and you have the discriminator for *any* Nutanix v4 resource. One proxy, every RestDefinition. Irregular cases get an `OBJECTTYPE_OVERRIDES` escape hatch.

---

## The quickstart: VM from YAML

With the proxy deployed and the slice patched, the full flow is four `kubectl` steps.

**1 — Deploy the proxy** (no registry needed; it's a single stdlib script):

```bash
kubectl -n nutanix-system create configmap nutanix-proxy-src \
  --from-file=nutanix_v4_proxy.py=quickstart/middleware/nutanix_v4_proxy.py
# set PC_BASE to https://<your-pc>:9440/api in deploy.yaml
kubectl apply -f quickstart/middleware/deploy.yaml
```

**2 — Apply the RestDefinition** (with the patched slice pointed at the proxy):

```bash
kubectl apply -f generated/vmm/restdefinitions/vm.restdefinition.yaml
kubectl -n nutanix-system wait restdefinition/nutanix-vmm-vm --for=condition=Ready
```

**3 — Provide credentials** via a `VmConfiguration` + `Secret`.

**4 — Create the VM** — apply the `Vm` CR from above:

```bash
kubectl apply -f vm.yaml
kubectl -n nutanix-system get vms.vmm.nutanix.krateo.io quickstart-vm
# NAME            READY   ...   SYNCED=True
```

The controller does `findby (?name=…) → not found → POST → 202 → (proxy polls the task) → 200`. And in Prism Central:

> **[Screenshot: `img/02-vm-list.png`]** — *the `quickstart-vm` row (1 vCPU, 2 GiB, AHV) in the Prism Central VM list.*

> **[Screenshot: `img/03-vm-details.png`]** — *the VM summary, with the description we set in the CR: "Created by the Krateo KOG operator via the Nutanix v4 middleware."*

No console clicks, no API scripts — a Kubernetes object reconciled into a real Nutanix VM.

---

## Why this is more than a VM

It's tempting to read this as "we made one resource work." It's actually broader:

- **The proxy is generic.** Because `$objectType` is derived and the other four translations are resource-agnostic, the *same* proxy will serve `Category`, `Subnet`, `VolumeGroup`, and the other ~180 Nutanix v4 resources in the repo — each just needs its `RestDefinition` and the three slice fixes. The hard part is solved once.
- **The fixes have a home upstream.** The codegen corrections belong in the oasgen-provider templates; the five translations could become a Nutanix "provider plugin" inside `rest-dynamic-controller`, retiring the sidecar entirely. The proxy is the proof-of-concept and the stopgap.
- **It's the GitOps story for Nutanix.** Once a resource is a CRD, everything you already do — Argo CD, policies, RBAC, drift detection — applies for free.

The pattern generalizes past Nutanix, too. Any API with a discriminator, idempotency keys, async jobs, or ETags can be brought under a generic OpenAPI operator with a thin, declarative translation layer instead of a bespoke controller.

---

## Try it

The proxy, manifests, patched slice, and full walkthrough are in the repo:

- **Quickstart:** `quickstart/README.md`
- **Proxy:** `quickstart/middleware/nutanix_v4_proxy.py` (stdlib-only) + `Dockerfile` + `deploy.yaml`

Point it at your Prism Central, apply a `Vm`, and watch it appear. Then try a `Category` — and notice you didn't write a single line of controller code for either.

---

## Appendix: the available RestDefinitions

The repo ships **189 RestDefinitions across 19 Nutanix v4 namespaces**. Each becomes a CRD + controller through the same flow shown above — `Vm` is just the worked example.

**aiops (6)** — EntityDescriptor, EntityType, Report, Scenario, Simulation, Source

**clustermgmt (20)** — BmcInfo, Cluster, ClusterProfile, Datastore, Disk, Host, Host2, HostNic, PcieDevice, PhysicalGpuProfile, RackableUnit, RsyslogServer, Snmp, StorageContainer, TaskResponse, Trap, User, VcenterExtension, VirtualGpuProfile, VirtualNic

**datapolicies (1)** — ProtectionPolicy

**dataprotection (4)** — ProtectedResource, RecoveryPoint, VmRecoveryPoint, VssMetadata

**files (22)** — AntiVirusServer, DnsRecord, EmailConfig, FileServer, InfectedFile, MountTarget, NotificationPolicy, ObjectStoreProfile, PartnerServer, QuotaPolicy, RansomwareConfig, Recommendation, ReplicationJob, ReplicationPolicy, Snapshot, SnapshotChangedContent, SnapshotSchedule, TierConfiguration, UnifiedNamespace, UserMapping, VdiUserSession, VirusScanPolicy

**iam (13)** — AuthorizationPolicy, BucketsAccessKey, CertAuthProvider, Client, DirectoryService, Entity, Key, Operation, Role, SamlIdentityProvider, SamlSpMetadata, User, UserGroup

**licensing (10)** — Allowance, Compliance, Entitlement, Eula, Feature, License, LicenseKey, Recommendation, Setting, Violation

**lifecycle (8)** — Bundle, Config, Entity, Image, LcmSummary, Notification, Recommendation, Status

**microseg (6)** — AddressGroup, CategoryMapping, DirectoryServerConfig, Policy, Rule, ServiceGroup

**monitoring (8)** — Alert, Audit, ClusterConfig, EmailConfig, Event, SystemDefinedPolicy, Tag, UserDefinedPolicy

**multidomain (1)** — ExternalRepository

**networking (30)** — BgpRoute, BgpSession, Capability, Capability2, Controller, FloatingIp, Gateway, IpfixExporter, Layer2Stretch, LearnedMacAddress, LoadBalancerSession, NodeSchedulableStatus, RemoteSubnet, RemoteVpnConnection, RemoteVtepGateway, ReservedIp, Route, RouteTable, RoutingPolicy, Subnet, Subnet2, TrafficMirror, UplinkBond, VirtualSwitch, Vnic, Vpc, Vpc2, VpcVirtualSwitchMapping, VpnConnection, VpnVendorConfig

**objects (3)** — Certificate, CertificateAuthority, ObjectStore

**opsmgmt (6)** — ContentFile, File, GlobalReportSetting, Report, ReportArtifact, ReportConfig

**prism (8)** — BackupTarget, Batch, Category, DomainManager, RestorableDomainManager, RestorePoint, RestoreSource, Task

**security (5)** — ApprovalPolicy, Credential, KeyManagementServer, Stig, StigSummary

**storage (9)** — CategoryAssociation, Datastore, Disk, IscsiClient, IscsiClientAttachment, MetadataInfo, StorageContainer, VmAttachment, VolumeGroup

**vmm (22)** — AhvVmComplianceState, CdRom, Disk, EffectiveRateLimitPolicy, EsxiVm, File, Gpu, GuestTool, Image, LegacyVmAntiAffinityPolicy, Nic, NutanixGuestTool, PcieDevice, PlacementPolicy, RateLimitPolicy, SerialPort, Template, Version, **Vm**, VmAntiAffinityPolicy, VmComplianceState, VmHostAffinityPolicy

**volumes (7)** — CategoryAssociation, Disk, ExternalIscsiAttachment, IscsiClient, Metadata, VmAttachment, VolumeGroup

---

*Built with [Krateo](https://krateo.io) (oasgen-provider / rest-dynamic-controller) against Nutanix Prism Central GA v4.0.*
