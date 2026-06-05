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

Combined with the four quickstart creatables (`Vm`, `Category`, `VolumeGroup`, `AddressGroup`),
**13 creatable RDs are operator-verified on the live PC** — plus the 23 read-observe →
**36 RDs live-tested green** so far.

Remaining testable (next batches, same serialized runner): `authorizationpolicy` (role ref),
`userdefinedpolicy`, `protectionpolicy`, `image` (ISO URL), `recoverypoint` (VM ref), and the
parent-chained children (`vm`→{disk,nic,serialport,cdrom}, `volumegroup`→disk, `user`→{key,accesskey},
`template`→version).

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
