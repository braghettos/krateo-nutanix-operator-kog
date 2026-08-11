---
type: Configuration
title: krateo-nutanix-operator-kog — configuration
description: The full configuration surface — nutanix-v4-proxy values and env, the nutanix-virtualmachine and nutanix-chain-lookup blueprint values, and the RestDefinition mapping conventions.
resource: https://github.com/krateo-blueprints/krateo-nutanix-operator-kog
tags: [nutanix, configuration, values, proxy, blueprint]
timestamp: 2026-08-11T00:00:00Z
---

# Configuration

## `charts/nutanix-v4-proxy`

Values (`charts/nutanix-v4-proxy/values.yaml`); `config.pcBase` is the only required
value — the chart `fail`s the render without it.

| key | default | purpose |
|---|---|---|
| `image.repository` / `image.tag` | `ghcr.io/krateo-blueprints/nutanix-v4-proxy` / `0.4.0` | proxy image; set `image.digest` to pin |
| `replicaCount` | `1` | proxy replicas |
| `config.pcBase` | `""` (**required**) | Prism Central API base, must end in `/api` (e.g. `https://pc.example.com:9440/api`) |
| `config.tlsVerify` | `false` | verify the PC TLS cert (PC often serves a private CA) |
| `config.taskTimeoutSeconds` | `180` | async task poll budget (seconds) |
| `config.xClusterId` | `""` | default `X-Cluster-Id` for cluster-scoped endpoints |
| `config.objectTypeOverrides` | `{}` | JSON map `{"<path-prefix>": "<$objectType>"}` for irregular paths |
| `config.logLevel` | `INFO` | `INFO` or `DEBUG` |
| `service.type` / `service.port` | `ClusterIP` / `8080` | the in-cluster Service |
| `resources` | 25m/32Mi → 250m/128Mi | requests/limits |

Each `config.*` value becomes a container env var (`templates/deployment.yaml`):
`PC_BASE`, `TLS_VERIFY`, `TASK_TIMEOUT_S`, `LOG_LEVEL`, and — when set — `X_CLUSTER_ID`
and `OBJECTTYPE_OVERRIDES`. The pod runs hardened by default: non-root (`65532`),
read-only rootfs, all capabilities dropped, `RuntimeDefault` seccomp; liveness/readiness
probe `/healthz`.

## `blueprints/nutanix-virtualmachine`

Values (`blueprints/nutanix-virtualmachine/values.yaml`), fully typed by
`values.schema.json` (which is what core-provider derives the generated CRD's schema
from). `vm.clusterExtId` is required — the template `fail`s without it.

| value | default | purpose |
|---|---|---|
| `configuration.create` | `true` | render the `VmConfiguration`; set `false` to reuse a shared one already on the cluster |
| `configuration.name` / `.namespace` | `nutanix-pc` / `nutanix-system` | name/namespace of the `VmConfiguration` and `Vm` |
| `configuration.authSecret.name` / `.namespace` | `nutanix-pc-auth` / `nutanix-system` | Secret holding PC `username`/`password` |
| `vm.name` | `krateo-bp-vm` | VM name (also the `Vm` resource name) |
| `vm.description` | *(blueprint text)* | free-text VM description |
| `vm.numSockets` / `vm.numCoresPerSocket` | `1` / `1` | vCPU sizing |
| `vm.memorySizeBytes` | `2147483648` (2 GiB) | memory in bytes (min `134217728`) |
| `vm.clusterExtId` | `""` (**required**) | registered Prism Element cluster extId that hosts the VM |
| `vm.categories` | `[]` | optional list of Nutanix category extIds |
| `disks[]` | one 20 GiB SCSI disk | inline disks: `{sizeBytes, busType, storageContainerExtId}` (`busType` enum `SCSI`/`IDE`/`PCI`/`SATA`/`SPAPR`) |
| `nics[]` | `[]` | inline NICs: `{subnetExtId, nicType}` (`nicType` enum `NORMAL_NIC`/`DIRECT_NIC`/`NETWORK_FUNCTION_NIC`/`SPAN_DESTINATION_NIC`) |
| `serialPorts[]` | `[]` | inline serial ports: `{index, isConnected}` |

Notes from the template (`templates/vm.yaml`): `extId` is never set (the controller
discovers it) and `powerState` is omitted (rejected on create). Large integers are
rendered via `int64`/`int` so Helm does not emit scientific notation, which would break
the integer fields. Each disk's `backingInfo.$objectType` is set to
`vmm.v4.ahv.config.VmDisk`, and `diskAddress.index` is assigned per bus type.

## `blueprints/nutanix-chain-lookup`

Values (`blueprints/nutanix-chain-lookup/values.yaml`):

| value | default | purpose |
|---|---|---|
| `configuration.name` / `.namespace` | `nutanix-pc` / `nutanix-system` | name/namespace of the `VmConfiguration` and `SerialPortConfiguration` |
| `configuration.authSecret.name` / `.namespace` | `nutanix-pc-auth` / `nutanix-system` | Secret holding PC credentials |
| `vm.name` | `krateo-lk-vm` | parent VM name (also the `lookup` key) |
| `vm.memorySizeBytes` / `vm.numSockets` / `vm.numCoresPerSocket` | 2 GiB / 1 / 1 | parent VM sizing |
| `vm.clusterExtId` | `""` | registered PE cluster extId |
| `child.serialPortIndex` | `1` | index of the dependent `SerialPort` |

The child template renders the `SerialPort` only once `lookup` resolves the parent VM's
`status.extId` into `spec.vmExtId`; each KOG kind needs its own typed
`<Kind>Configuration`, so this chart renders both `VmConfiguration` **and**
`SerialPortConfiguration`.

## RestDefinition mapping conventions

The generated `RestDefinition`s (`generated/<ns>/restdefinitions/`) are configured by the
generator (`scripts/generate_restdefinitions.py`), not by end-user Helm values, but the
conventions matter operationally:

- Verbs map to endpoints: `findby` = GET collection, `create` = POST collection,
  `get`/`update`/`delete` = GET/PUT/DELETE on `collection/{id}`.
- `identifiers` prefer `name`; the `{id}` path param is fed from `status.extId`.
- OData query params (`$filter`, `$page`, `$limit`, …) go in `excludedSpecFields` so
  they are not treated as desired state.
- `identifiers` are **immutable** post-generation — change them only via delete+recreate.
- The OAS slice's `servers[0].url` points at the `nutanix-v4-proxy` Service.

See `generated/README.md` for the full production recipe and `generated/ANALYSIS.md` for
the per-resource verb/sync-async inventory.
