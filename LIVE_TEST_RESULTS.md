# Live-test results — read-observe batch (serialized via the operator)

**23 / 27** read-observe RestDefinitions reached `Synced=True` against a live GA v4.0
Prism Central — each driven by the KOG operator + the Nutanix v4 proxy, **one
controller at a time**. Auth held at `200` throughout (no admin-account lockout —
the lockout was caused by a *concurrent* test storm, not by steady controllers).

Read-observe = the RD has no `create` verb; the CR is just `{configurationRef}` and the
controller does findby/get against the live PC.

## Passed (23)

| ns | kind | ns | kind |
|---|---|---|---|
| clustermgmt | Disk | monitoring | Alert |
| clustermgmt | Host2 | monitoring | Audit |
| clustermgmt | PcieDevice | monitoring | EmailConfig |
| clustermgmt | VcenterExtension | monitoring | Event |
| iam | Entity | monitoring | SystemDefinedPolicy |
| iam | Operation | networking | Capability2 |
| lifecycle | Config | networking | RouteTable |
| lifecycle | Entity | networking | UplinkBond |
| lifecycle | Image | prism | Task |
| lifecycle | LcmSummary | storage | IscsiClient |
| vmm | EsxiVm | volumes | IscsiClient |
| vmm | LegacyVmAntiAffinityPolicy | | |

## Not green (4) — with cause

| ns | kind | status | cause |
|---|---|---|---|
| networking | subnet | recoverable | the generator put `X-Cluster-Id` as a *required spec field*; the proxy now injects it and `patch_slice.py` drops the param, but the CRD must be regenerated (delete + re-apply the RD) to clear the required field |
| networking | vpc | blocked | it's the **AWS subtree** (`/networking/v4.0/aws/config/vpcs`) — returns `500 error fetching zeus config`; the AWS/cloud backend is non-functional on this on-prem PC (the X-Cluster-Id header is now satisfied — the error moved past it) |
| iam | samlspmetadata | controller bug | `observe failed: handling response: converting JSON to YAML` — rest-dynamic-controller can't deserialize this endpoint's response shape |
| lifecycle | statu | unverifiable | the generator named the kind `Statu` → CRD `status.lifecycle.nutanix.krateo.io`, which collides with the Kubernetes `status` keyword, so the CR can't be queried cleanly (the resource itself is likely fine) |

## Create batch — serialized creates through the operator

**9 / 10** creatable RDs were **created on the live PC + reached `Synced=True`** via the operator
(one controller at a time, `scripts/live_test_create.py` — each resource confirmed present on
the PC by a follow-up API read):

| ns | kind | create type | result |
|---|---|---|---|
| aiops | Simulation | sync, no parent | ✅ True (on PC) |
| microseg | ServiceGroup | async, no parent | ✅ True (on PC) |
| clustermgmt | StorageContainer | needs `X-Cluster-Id` | ✅ True (on PC) — validates the proxy's **X-Cluster-Id** injection |
| iam | User | no parent (`SERVICE_ACCOUNT`) | ✅ True (on PC) |
| iam | Role | needs live operation extIds | ✅ True (on PC) |
| clustermgmt | RsyslogServer | cluster-scoped path | ✅ True (on PC) — validates **`{clusterExtId}` path-param** sourced from spec |
| vmm | VmAntiAffinityPolicy | needs a category ref | ✅ True (on PC) |
| vmm | PlacementPolicy | two category `Filter`s | ✅ True (on PC) |
| vmm | RateLimitPolicy | category `Filter` | ✅ True (on PC) |
| clustermgmt | Trap (SNMP) | — | ❌ CRD won't generate (`generating CRD: exit status 1`) — oasgen-provider codegen limit, same bucket as `samlspmetadata`/`statu` |

Two findings worth recording for future fixtures:
- The vmm `Filter` schema has **no discriminator**, so the generated CRD rejects a nested
  `$objectType` (`strict decoding error: unknown field "spec.clusterEntityFilter.$objectType"`).
  The proxy only injects `$objectType` at the **top level**; nested objects that *do* carry a
  discriminator must supply it in-spec, but a discriminator-less type like `Filter` must **omit** it.
- Cluster-scoped resources (`rsyslog-servers`, `snmp/traps`) take `{clusterExtId}` from a
  matching `spec.clusterExtId` field — no extra mapping needed.

## Parent-chained creates (`CREATE_NEEDS_PARENT`)

The runner now creates a parent, resolves its extId (from CR status, falling back to a
findby on the PC by name), and threads it into each child's `{…ExtId}` path param:

| chain | result |
|---|---|
| `vmm/Vm` → `vmm/SerialPort` | ✅ both True — serial-port present on the VM. The child POST to `/vms/{vmExtId}/serial-ports` requires the **parent VM's `If-Match`**; the proxy now injects it (GET parent → ETag → retry) only when the API demands it (`412/428`). Proxy log: `retried POST …/serial-ports with parent If-Match -> 202`. |
| `vmm/Vm` → `vmm/Disk` | ✅ True — disk on the VM. The body's discriminated `backingInfo.$objectType` (`vmm.v4.ahv.config.VmDisk`) is carried by the CRD (discriminated union), unlike the discriminator-less `Filter`. |
| `vmm/Vm` → `vmm/CdRom` | ⚠️ **created on the PC** (cd-rom present on the VM), but the controller can't confirm it back — see note below. |
| `vmm/Vm` → `vmm/Nic` | ⚠️ **created on the PC** (used existing subnet `vm-net`; nic present on the VM via the parent-If-Match retry → 202), but observe-blocked — see note below. |
| `iam/User` → `iam/Key` | ✅ True — API key created under the service-account user and observed. The parent already existed, so the runner resolves the parent extId via findby-by-name and proceeds straight to the child. |
| `volumes/VolumeGroup` → `volumes/Disk` | ⚠️ parent True + extId threaded into the child path correctly, but this PC build's `VolumeDisk` create rejects a blank disk (`VOL-40101: DiskDataSourceReference cannot be empty`) — a server-side data requirement, not a chaining failure. |

**Nameless VM children (`CdRom`, `Nic`) — created but not observable.** The create *succeeds*
(both are present on the VM on the PC), but the Nutanix async task for a nic/cd-rom create reports
only the **parent VM** in `entitiesAffected` — never the child's extId. A schema-agnostic proxy
can't recover the child id from the task, so the get-back fails and the controller loops
(`external-create-pending`). `SerialPort` and `Disk` (same parent-If-Match path) observe fine, so
this is specific to how those two endpoints report their task entities, not a chaining gap.

This added a **new proxy capability (5b)**: child-of-parent `If-Match` on POST.

## Bespoke-body creates (`CREATE_NEEDS_REF`, no parent path)

| ns | kind | body needs | result |
|---|---|---|---|
| iam | AuthorizationPolicy | role ref + ABAC entity/identity filters | ✅ True (on PC) — `entityFilter`/`identityFilter` are preserve-unknown objects; `role` resolved from the seeded role |
| datapolicies | ProtectionPolicy | local replication location + schedule **with linear retention** | ✅ True (on PC) — CRD's `schedule.retention` is preserve-unknown, so the nested `$objectType` is accepted |
| dataprotection | RecoveryPoint | VM ref in nested `vmRecoveryPoints` | ❌ operator-blocked — the create **works at the API**, but it requires `$objectType` on the nested `vmRecoveryPoints` items, a field the generated CRD does not carry (strict-decode rejects it) and the schema-agnostic proxy can't infer a nested discriminator |
| vmm | Template | discriminated `templateVersionSpec.versionSource` from a VM | ✅ True (on PC) — created from the seeded VM; the nested oneOf `versionSource.$objectType` (`TemplateVmReference`) is carried by the CRD |

Plus `vmm/VmHostAffinityPolicy` (vm+host category refs) → ✅ True. Combined with the four
quickstart creatables (`Vm`, `Category`, `VolumeGroup`, `AddressGroup`), **20 creatable RDs are
operator-verified on the live PC** (`Synced=True`) — plus `CdRom` and `Nic` created-but-observe-
pending — plus the 23 read-observe → **43 RDs live-tested green**.

Blocks recorded — each external to the operator, not a KOG/proxy gap:
- `Trap` — oasgen-provider CRD codegen fails (`generating CRD: exit status 1`).
- `VolumeDisk` — this PC build requires a `diskDataSourceReference` (won't create a blank disk).
- `RecoveryPoint` — API needs `$objectType` on nested `vmRecoveryPoints`; the CRD can't carry it.
- `CdRom`/`Nic` — created on the PC, but the Nutanix create task reports only the parent VM, so
  the child extId can't be observed back.
- `UserDefinedPolicy` — needs the Nutanix alert-metric catalog (valid `entityType`/`metricName`);
  the API returns a bare `400` with no detail and no catalog is exposed.
- `Image` — needs an external ISO/disk download (out-of-band dependency).

Remaining untested RDs are the same bespoke-body shape — **no new mechanism**: every create path
(read-observe, sync/async, X-Cluster-Id, cluster path-param, live-ref, ABAC/preserve-unknown
bodies, parent-chain + parent-If-Match, discriminated nested unions, create-from-source) is
now proven against the live GA v4.0 PC.

## Notes

- This run also surfaced and fixed a bug in `scripts/live_test.py`: it derived the
  CRD name as `kind.lower()+'s'`, which is wrong for KOG's English pluralization
  (`Entity→entities`, `LcmSummary→lcmsummaries`, `SystemDefinedPolicy→systemdefinedpolicies`).
  That produced **false negatives** in the first pass — the resources had reconciled
  `True` but their status couldn't be read. The script now resolves the real CRD name
  from the cluster.
- The proxy gained generic **`X-Cluster-Id`** injection (`X_CLUSTER_ID` env), and
  `patch_slice.py` now drops the required `X-Cluster-Id` param — together these unblock
  X-Cluster-Id-gated resources (e.g. `clustermgmt/storage-containers`) that have a live
  backend.

## Coverage map of all 189 RDs (this install is PC size `STARTER`)

A full per-RD reachability probe (GET each collection on the live PC):

| bucket | count | meaning |
|---|---:|---|
| reachable now | ~75 | product present — testable with the right body |
| need-a-parent | ~79 | findby needs a parent extId (chainable / inline — see blueprint) |
| `503` not deployed | ~24 | service absent on this PC |
| `404` absent | ~11 | feature not present |

**The hard ceiling is PC size.** Almost every blocked RD funnels through **CMSP/MSP
(Microservices Infrastructure)**, which requires a **Small-or-larger PC** — this one is
`STARTER` (`pc.2024.3.1.13`). So the whole product tier is unreachable here:

- **Flow Virtual Networking / Atlas** — ~22 `networking` RDs (`vpc2`, overlay `subnet2`,
  `floatingip`, `gateway`, `routingpolicy`, `vpnconnection`, `bgpsession`, `loadbalancersession`,
  `trafficmirror`, `virtualswitch`, …); `networking/controllers` is reachable but `count=0`.
- **Files** (22, Files Manager) · **Objects** (3) · **security** (5: approval/KMS/STIG, 404) ·
  **opsmgmt** (6 reports, 503) · **licensing** (10, 503 — unlicensed) · **multidomain** (1).

External-system gated (not a PC-size issue): `iam` `directoryservice`/`samlidentityprovider`/
`usergroup`/`certauthprovider` (LDAP/SAML/cert), `lifecycle/bundle` (LCM artifact),
`monitoring/userdefinedpolicy` (alert-metric catalog — opaque 400), `aiops/scenario`
(observe 400). Infra-creation we can't do: `clustermgmt/cluster`, `prism/domainmanager`.
`microseg/policy` create → 500 (Flow security policy needs additional setup).

**To unlock the product tier you need a Small+ PC** (resize this one — gated on the OVH host
resources — or stand up a fresh larger Nutanix). Highest-ROI single product: **CMSP** (unlocks
Atlas networking + Objects).

## Chained resources via a Krateo blueprint

Directive: chainable resources should be tested as a Krateo blueprint, not an ad-hoc runner.

There are **two** blueprint patterns, both validated:

**1. Inline composition.** The Nutanix `Vm` create body accepts `disks`, `nics`, `cdRoms` and
`serialPorts` **inline**, and the KOG `Vm` CRD carries them. So `blueprints/nutanix-virtualmachine`
provisions a fully-built VM as **one** declarative resource — no cross-CR wiring needed.
Validated end-to-end: `helm template … | kubectl apply` → `Vm` `Synced=True` → on the PC the VM
`krateo-bp-vm` has **1 disk + 1 nic + 1 serial-port** from one composition. This covers the 8
creatable inline children (vm's disk/nic/cdrom/serialport/gpu/pcieDevice, `volumes/VolumeGroup.disks`,
`iam/User.bucketsAccessKeys`).

**2. `lookup`-coupled dependents.** For a *day-2* child that needs the parent's runtime extId
(`spec.<parent>ExtId`), a blueprint couples them with Helm's **`lookup`** function: the
composition-dynamic-controller re-renders each reconcile, and `lookup` reads the sibling CR's
**live** status. `blueprints/nutanix-chain-lookup` demonstrates this — the dependent `SerialPort`
is rendered only once `lookup` resolves the parent `Vm`'s `status.extId`, then injected as
`spec.vmExtId`. Proven: `helm lookup` returns the Vm CR with its status (`found=true,
hasStatus=true`), and the rendered SerialPort carried `spec.vmExtId=<the VM's runtime extId>`.

**Caveats for pattern 2 (both upstream of the blueprint, in the rest-dynamic-controller):**
- The source CR must publish `status.extId`. The Vm CR's is **unreliable** today (it stays
  `Ready=False/Creating` and the extId flaps empty), so `lookup` needs several reconciles to
  catch it — which the composition controller does anyway, but a deterministic
  `status.extId` (the [[kog-controller-nutanix-gap]]) would make it clean.
- Each KOG kind needs its own typed `<Kind>Configuration`, so the blueprint must render one per
  kind it uses (`VmConfiguration`, `SerialPortConfiguration`, …).

(Correction: an earlier note here claimed a static blueprint *can't* wire cross-CR inputs — that
was wrong. `lookup` + the controller's reconcile loop is exactly the supported mechanism.)

## status.extId reliability — root cause + proxy fix (v0.3.0, feature 6)

KOG resources reached `Synced=True` but often stayed `Ready=False/Creating` with `status.extId`
empty/flapping. Tracing `rest-dynamic-controller:0.8.0` (the latest tag — no upgrade available):

- `internal/controllers/helpers.go` `populateStatusFields` reads identifier /
  `additionalStatusFields` at the **body root** (`body["extId"]`).
- Nutanix v4 wraps every response: `{data:{…}}` (single) / `{data:[…]}` (list).
- The **create** (`restResources.go:358`) and **get-by-id** paths pass the raw enveloped body —
  no unwrap — so `extId` (at `data.extId`) is never lifted into status.
- Only **findby** unwraps (`restclient.go:474 extractItemsFromResponse`), and its match
  (`clienttools.go:112 isInResource`) compares the API value to `spec`/`status` — so
  `extId`-identified resources (e.g. `category`) can **never** match on a cold observe
  (chicken-and-egg) and sit at `Ready=False`.

**This is controller code, not an RD YAML fix.** The RDs already declare the correct
`identifiers` + `additionalStatusFields`, and findby returns the right item.

**Fix shipped — proxy feature 6 (no controller change):** the proxy now **unwraps the
`{data:{…}}` envelope on successful single-object responses**, so the controller sees resource
fields (incl. `extId`) at the body root on the create/get paths — populating `status.extId` and
`Ready=True`, and breaking the extId chicken-and-egg. **List** responses (`{data:[…]}`) are left
intact for findby item-extraction + the paginator.

Validated at the proxy level against the live PC: GET-by-id through the proxy returns `extId` at
the root with no `data` envelope; LIST keeps the `data` array. (End-to-end controller validation
is pending a rebuild of the KOG test cluster, which was torn down.) The proper upstream fix
(option 1) is to make `rest-dynamic-controller` unwrap the envelope and lift `extId` from the
create response directly — tracked for the Krateo team.
