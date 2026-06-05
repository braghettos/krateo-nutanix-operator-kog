# nutanix-chain-lookup (Krateo blueprint demo)

Demonstrates coupling KOG custom resources whose inputs come from **another CR**, using a
Krateo blueprint + Helm's **`lookup`** function — the supported way to wire a day-2 dependent
to a parent's runtime value.

The dependent `SerialPort` needs the parent VM's runtime `status.extId` in `spec.vmExtId`.
The child template does:

```gotemplate
{{- $vm := lookup "vmm.nutanix.krateo.io/v1alpha1" "Vm" $ns .Values.vm.name -}}
{{- $ext := "" }}{{- if $vm }}{{- $ext = dig "status" "extId" "" $vm }}{{- end }}
{{- if $ext }}
# ... SerialPort with vmExtId: {{ $ext }}   <-- coupled from the sibling Vm CR
{{- end }}
```

`lookup` reads **live** cluster state, so it returns nothing during `helm template`/first render
and resolves once the parent exists. Krateo's composition-dynamic-controller re-renders on every
reconcile, so the dependent is created on a later pass — no manual ordering.

## Proven

- `helm lookup` on the `Vm` CR returns it **with its status** (`found=true, hasStatus=true`).
- The blueprint rendered the `SerialPort` with `spec.vmExtId` = the VM's runtime extId from lookup.

## Caveats (upstream of the blueprint — in the rest-dynamic-controller)

- The parent CR must **reliably publish `status.extId`**. The Vm CR's is currently flaky (stays
  `Ready=False/Creating`, extId flaps empty), so `lookup` needs several reconciles to catch it.
  A deterministic `status.extId` makes this clean.
- Each KOG kind needs its own typed `<Kind>Configuration`; render one per kind (this chart
  renders `VmConfiguration` **and** `SerialPortConfiguration`).

## Run (simulating the controller's reconcile loop with `helm upgrade`)

```bash
helm upgrade --install lk blueprints/nutanix-chain-lookup -n nutanix-system \
  --set configuration.name=nutanix-pc-lk \
  --set vm.clusterExtId=<PE-cluster-extId>
# repeat the upgrade; once the Vm's status.extId is set, the SerialPort renders coupled.
```
