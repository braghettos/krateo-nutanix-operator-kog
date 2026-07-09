# nutanix-virtualmachine (Krateo blueprint)

Provisions a complete Nutanix AHV VM — **disks, NICs and serial ports declared inline on the
VM** — as a single KOG `Vm` resource. This is the composition-friendly way to model what would
otherwise be a parent→child chain.

## Prerequisites

The target cluster must already have:

- **KOG** (`oasgen-provider`) + the generated **`Vm` RestDefinition** applied, with `extId` in
  its `excludedSpecFields` so the generated CRD does **not** require `extId`. (An older RD that
  requires it forces a bogus value, and the controller then does a get-by-id on that non-UUID →
  Prism `400`. If you hit that, patch the CRD:
  `kubectl patch crd vms.vmm.nutanix.krateo.io --type=json -p '[{"op":"replace","path":"/spec/versions/0/schema/openAPIV3Schema/properties/spec/required","value":["configurationRef"]}]'`.)
- The **`nutanix-v4-proxy` middleware ≥ v0.4.0** (`nutanix-mw` Service), which the `Vm` OAS
  slice points at. **v0.4.0 is required for `Ready=True`**: earlier builds leave large integers
  (`memorySizeBytes`) mismatched on observe, so the controller re-updates every reconcile and
  never goes Ready.
- A **Secret** with the Prism Central `username`/`password` (default `nutanix-pc-auth` in
  `nutanix-system`).
- For the composition path: a full **Krateo** install (`core-provider` +
  `composition-dynamic-controller`).

## Why inline (and not separate child resources)

The Nutanix v4 `Vm` *create* body accepts `disks`, `nics` and `serialPorts` inline, and the
KOG-generated `Vm` CRD carries those fields (the disk `backingInfo` is preserved via
`x-kubernetes-preserve-unknown-fields`, so its `$objectType` discriminator survives). So the
blueprint renders **one** declarative resource and the VM comes up fully built — **no runtime
extId wiring required**. *(CD-ROMs are not yet exposed by this blueprint.)*

The standalone child RestDefinitions (`vmm/Disk`, `vmm/Nic`, `vmm/SerialPort`, `vmm/CdRom`,
`volumes/Disk`, `iam/Key`, …) take the parent's **runtime extId** in `spec.<parent>ExtId`
(their `create` uses `requestFieldMapping: [{inPath: vmExtId, inCustomResource: spec.vmExtId}]`,
a JSONPath within the same CR). For **initial provisioning** the inline form above avoids the
problem entirely.

For **day-2** children of an existing VM, couple them with a blueprint + Helm's **`lookup`**
function — see `../nutanix-chain-lookup`. ⚠️ That path depends on the parent `Vm` reliably
publishing `status.extId`, and `rest-dynamic-controller` 0.8.0 does **not** keep it populated
from the cold-create findby-list path (it only sticks via the get-by-id path). Treat the day-2
lookup chain as experimental until that's addressed upstream. See `LIVE_TEST_RESULTS.md`.

## Use

Standalone (renders the KOG `Vm` + its `VmConfiguration`):

```bash
helm template my-vm blueprints/nutanix-virtualmachine \
  --set vm.clusterExtId=<PE-cluster-extId> \
  --set 'disks[0].sizeBytes=21474836480' \
  --set 'nics[0].subnetExtId=<subnet-extId>' | kubectl apply -f -
```

As a Krateo composition: package + publish the chart, apply `compositiondefinition.yaml`, then
apply a `NutanixVirtualmachine` composition (see `examples/composition.yaml`) — the
composition-dynamic-controller renders this same chart. Verified end-to-end on a live PC:
composition → `Vm` `Synced=True, Ready=True/Available` with an inline disk + serial port.

| value | purpose |
|---|---|
| `vm.clusterExtId` | **required** — registered PE cluster extId |
| `vm.{numSockets,numCoresPerSocket,memorySizeBytes,categories}` | VM sizing + categories |
| `disks[]` | `{sizeBytes, busType, storageContainerExtId}` — inline disks |
| `nics[]` | `{subnetExtId, nicType}` — inline NICs |
| `serialPorts[]` | `{index, isConnected}` — inline serial ports |
| `configuration.create` | render the `VmConfiguration` (set `false` to reuse a shared one) |
| `configuration.authSecret` | secret holding PC `username`/`password` |
