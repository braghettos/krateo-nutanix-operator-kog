---
type: Example
title: nutanix-virtualmachine — a Nutanix AHV VM as a Krateo composition
description: A runnable example that provisions a complete Nutanix AHV virtual machine (disks, NICs and serial ports declared inline) as a single KOG Vm resource, via the nutanix-virtualmachine blueprint — standalone or as a Krateo composition.
resource: https://github.com/krateo-blueprints/krateo-nutanix-operator-kog
tags: [example, nutanix, virtualmachine, blueprint, composition]
timestamp: 2026-08-11T00:00:00Z
---

# nutanix-virtualmachine

Provisions a complete **Nutanix AHV VM** — with its disks, NICs and serial ports declared
**inline** on the VM — as a single KOG `Vm` resource (plus the `VmConfiguration` that
holds the Prism Central credentials). This is the composition-friendly way to model what
would otherwise be a parent→child chain: the Nutanix v4 `Vm` create body accepts
disks/nics/serialPorts inline, so no runtime `extId` wiring is needed.

`composition.yaml` here is a `NutanixVirtualmachine` composition —
`composition.krateo.io/v0-3-0`, the API core-provider derives from the blueprint chart
(`nutanix-virtualmachine` → Kind `NutanixVirtualmachine`, version `0.3.0` →
`v0-3-0`).

## Preconditions

- **KOG** (`oasgen-provider`) with the generated `vmm/Vm` RestDefinition applied and
  `READY=True` (keep `extId` in its `excludedSpecFields`).
- The **`nutanix-v4-proxy` ≥ v0.4.0** deployed as the `nutanix-mw` Service (v0.4.0 is
  required for `Ready=True`).
- A **Secret** `nutanix-pc-auth` in `nutanix-system` with keys `username`/`password`.
- For the composition path: a full **Krateo** install (`core-provider` +
  `composition-dynamic-controller`).

See the repo [usage](../../docs/usage.md) and [configuration](../../docs/configuration.md)
docs for the full walkthrough.

## Run it — standalone

Render the blueprint directly to the KOG `Vm` + `VmConfiguration` and apply:

```console
$ helm template my-vm blueprints/nutanix-virtualmachine \
    --set vm.clusterExtId=<PE-cluster-extId> \
    --set 'disks[0].sizeBytes=21474836480' | kubectl apply -f -
$ kubectl get vm -n nutanix-system                  # Synced=True, Ready=True/Available
```

## Run it — as a Krateo composition

1. Publish the chart and register the blueprint (see [release](../../docs/release.md)):

   ```console
   $ helm dependency build blueprints/nutanix-virtualmachine
   $ helm package blueprints/nutanix-virtualmachine
   $ helm push nutanix-virtualmachine-0.3.0.tgz oci://ghcr.io/krateo-blueprints/charts
   $ kubectl apply -f blueprints/nutanix-virtualmachine/compositiondefinition.yaml
   ```

2. Edit `composition.yaml` (set `vm.clusterExtId` to a registered PE cluster extId) and
   apply it:

   ```console
   $ kubectl apply -f examples/nutanix-virtualmachine/composition.yaml
   $ kubectl get nutanixvirtualmachine -n krateo-system
   ```

The composition-dynamic-controller renders the same chart into the `Vm` (+
`VmConfiguration`), and — because the chart depends on `portal-composition-page-generic`
— a full Krateo install also renders a Composition page in the portal (Events,
managed-resource Status, a Values form).
