---
type: API
title: krateo-nutanix-operator-kog — API
description: The custom resources this repo produces — the KOG-generated Nutanix resource CRDs and their typed Configuration CRDs, and the CompositionDefinition the VirtualMachine blueprint registers with Krateo.
resource: https://github.com/krateo-blueprints/krateo-nutanix-operator-kog
tags: [nutanix, api, crd, restdefinition, compositiondefinition]
timestamp: 2026-08-11T00:00:00Z
---

# API

Two layers of API are produced here: the **KOG-generated resource CRDs** (one per
Nutanix v4 resource, from the `RestDefinition`s) and the **`CompositionDefinition`** the
VirtualMachine blueprint registers so Krateo derives a composition CRD from the chart.

## KOG-generated resource CRDs

When `oasgen-provider` reconciles a `RestDefinition`, it generates, for each resource:

- a **resource CRD** — `<kind>.<ns>.nutanix.krateo.io/v1alpha1` (e.g.
  `vms.vmm.nutanix.krateo.io`, kind `Vm`). Its `spec` mirrors the sanitized OpenAPI
  schema of the Nutanix resource; its `status` carries `extId` and the standard
  Krateo/Crossplane conditions.
- a typed **`<Kind>Configuration` CRD** — holds the Prism Central credentials the
  controller uses. The resource CR references it by `spec.configurationRef`.
- a **`rest-dynamic-controller` Deployment** that reconciles instances of the resource
  CRD against the Nutanix v4 REST API (through the proxy).

There are **189** such resources across the **19** Prism Central v4 namespaces present in
`generated/` (`aiops`, `clustermgmt`, `datapolicies`, `dataprotection`, `files`, `iam`,
`licensing`, `lifecycle`, `microseg`, `monitoring`, `multidomain`, `networking`,
`objects`, `opsmgmt`, `prism`, `security`, `storage`, `vmm`, `volumes`). See
`generated/ANALYSIS.md` for the full per-resource list with verbs and sync/async.

### Minimal resource CR shape

```yaml
apiVersion: <ns>.nutanix.krateo.io/v1alpha1
kind: <Kind>
metadata:
  name: example
  namespace: nutanix-system
spec:
  configurationRef:
    name: nutanix-pc
    namespace: nutanix-system
  # ... resource fields
```

### `<Kind>Configuration` shape

Holds the credentials referenced by `spec.configurationRef`:

```yaml
apiVersion: vmm.nutanix.krateo.io/v1alpha1
kind: VmConfiguration
metadata:
  name: nutanix-pc
  namespace: nutanix-system
spec:
  authentication:
    basic:
      usernameRef:
        name: nutanix-pc-auth
        namespace: nutanix-system
        key: username
      passwordRef:
        name: nutanix-pc-auth
        namespace: nutanix-system
        key: password
```

### The `Vm` resource (used by the VirtualMachine blueprint)

The `vmm/Vm` RestDefinition generates `vms.vmm.nutanix.krateo.io` (kind `Vm`). Its spec
accepts disks, NICs and serial ports **inline** on the VM (the Nutanix v4 create body
does), which is what the VirtualMachine blueprint renders:

```yaml
apiVersion: vmm.nutanix.krateo.io/v1alpha1
kind: Vm
spec:
  configurationRef: {name: nutanix-pc, namespace: nutanix-system}
  name: krateo-bp-vm
  numSockets: 1
  numCoresPerSocket: 1
  memorySizeBytes: 2147483648
  cluster:
    extId: "<PE-cluster-extId>"
  disks:
    - backingInfo:
        $objectType: vmm.v4.ahv.config.VmDisk    # preserved via x-kubernetes-preserve-unknown-fields
        diskSizeBytes: 21474836480
      diskAddress: {busType: SCSI, index: 0}
  nics: []
  serialPorts: []
```

`extId` is not set (the controller discovers it); `powerState` is omitted (rejected on
create). An older `Vm` RestDefinition that *requires* `extId` breaks provisioning — keep
`extId` in the RestDefinition's `excludedSpecFields` so the generated CRD does not require
it (the blueprint README documents the CRD patch if you hit that).

## The blueprint `CompositionDefinition`

`blueprints/nutanix-virtualmachine/compositiondefinition.yaml` registers the VM blueprint
with a full Krateo install. `core-provider` reads it, pulls the published chart, derives
a composition CRD from the chart's `values.schema.json`, and stands up a
composition-dynamic-controller that renders the chart into the KOG `Vm` (+
`VmConfiguration`) on each reconcile.

```yaml
apiVersion: core.krateo.io/v1alpha1
kind: CompositionDefinition
metadata:
  name: nutanix-virtualmachine
  namespace: krateo-system
spec:
  chart:
    url: oci://ghcr.io/krateo-blueprints/charts/nutanix-virtualmachine
    version: 0.3.0
```

`spec.chart.version` must match the published chart version. From the chart's
`Chart.yaml`, core-provider derives the generated composition API: the **Kind** from
`name` (dashes dropped, CamelCased — `nutanix-virtualmachine` → `NutanixVirtualmachine`)
and the **apiVersion** from `version` (`0.3.0` → `composition.krateo.io/v0-3-0`). So a
composition instance looks like:

```yaml
apiVersion: composition.krateo.io/v0-3-0
kind: NutanixVirtualmachine
metadata:
  name: nutanix-virtualmachine
  namespace: krateo-system
spec:
  vm:
    clusterExtId: "<registered-PE-cluster-extId>"
  # ... see examples/composition.yaml and configuration.md
```

The `nutanix-chain-lookup` blueprint has no `CompositionDefinition` of its own — it is a
demo installed with `helm upgrade` (see [usage](./usage.md)).
