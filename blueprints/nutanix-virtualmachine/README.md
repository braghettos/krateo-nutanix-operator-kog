# nutanix-virtualmachine (Krateo blueprint)

Provisions a complete Nutanix AHV VM — **disks, NICs, CD-ROMs and serial ports declared
inline on the VM** — as a single KOG `Vm` resource. This is the composition-friendly way to
model what would otherwise be a parent→child chain.

## Why inline (and not separate child resources)

The Nutanix v4 `Vm` *create* body accepts `disks`, `nics`, `cdRoms` and `serialPorts` inline,
and the KOG-generated `Vm` CRD carries those fields. So a blueprint renders **one** declarative
resource and the VM comes up fully built — **no runtime extId wiring required**.

The standalone child RestDefinitions (`vmm/Disk`, `vmm/Nic`, `vmm/SerialPort`, `vmm/CdRom`,
`volumes/Disk`, `iam/Key`, …) take the parent's **runtime extId** in `spec.<parent>ExtId`
(their `create` uses `requestFieldMapping: [{inPath: vmExtId, inCustomResource: spec.vmExtId}]`,
a JSONPath within the same CR). For **initial provisioning** the inline form above avoids the
problem entirely.

For **day-2** children of an existing VM, couple them with a blueprint + Helm's **`lookup`**
function (the composition-dynamic-controller re-renders each reconcile and `lookup` reads the
sibling CR's live status) — see `../nutanix-chain-lookup` for a working demo that injects the
parent VM's `status.extId` into a dependent `SerialPort`. That path depends on the parent CR
reliably publishing `status.extId` (a rest-dynamic-controller detail). See `LIVE_TEST_RESULTS.md`.

## Use

Standalone (renders the KOG `Vm` + its `Configuration`):

```bash
helm template my-vm blueprints/nutanix-virtualmachine \
  --set vm.clusterExtId=<PE-cluster-extId> \
  --set 'disks[0].sizeBytes=21474836480' \
  --set 'nics[0].subnetExtId=<subnet-extId>' | kubectl apply -f -
```

As a Krateo composition (full Krateo install): package + publish the chart, then apply
`compositiondefinition.yaml` — the composition-dynamic-controller renders this same chart.

| value | purpose |
|---|---|
| `vm.clusterExtId` | **required** — registered PE cluster extId |
| `vm.{numSockets,numCoresPerSocket,memorySizeBytes,categories}` | VM sizing + categories |
| `disks[]` | `{sizeBytes, busType, storageContainerExtId}` — inline disks |
| `nics[]` | `{subnetExtId, nicType}` — inline NICs |
| `serialPorts[]` | `{index, isConnected}` — inline serial ports |
| `configuration.authSecret` | secret holding PC `username`/`password` |
