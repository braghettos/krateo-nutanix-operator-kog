---
type: Usage
title: krateo-nutanix-operator-kog — usage
description: How to use the family — apply the RestDefinitions, install the v4 proxy, and deploy the VirtualMachine blueprint standalone or as a Krateo composition, plus the day-2 chain-lookup demo.
resource: https://github.com/krateo-blueprints/krateo-nutanix-operator-kog
tags: [nutanix, kog, install, proxy, blueprint, composition]
timestamp: 2026-08-11T00:00:00Z
---

# Usage

## Prerequisites

The target cluster must have:

- **KOG** (`oasgen-provider`) installed — the `restdefinitions.ogen.krateo.io` CRD must
  be present. For the composition path (the blueprints), a full **Krateo** install
  (`core-provider` + `composition-dynamic-controller`).
- The **`nutanix-v4-proxy`** deployed (below), which the RestDefinition OAS slices point
  at. The VirtualMachine blueprint needs proxy **≥ v0.4.0** for `Ready=True` (earlier
  builds leave large integers like `memorySizeBytes` mismatched on observe, so the
  controller re-updates every reconcile and never goes Ready).
- A **Secret** holding the Prism Central `username`/`password` (default `nutanix-pc-auth`
  in namespace `nutanix-system`).

## Install the v4 proxy

From the published OCI registry (image + chart are pushed by CI on each `v*.*.*` tag):

```console
$ helm install nutanix-mw oci://ghcr.io/krateo-blueprints/charts/nutanix-v4-proxy --version 0.6.0 \
    -n nutanix-system --create-namespace \
    --set config.pcBase=https://<PC-HOST>:9440/api \
    --set config.xClusterId=<registered-PE-cluster-extId>      # optional
```

Or from a local checkout:

```console
$ helm install nutanix-mw charts/nutanix-v4-proxy -n nutanix-system --create-namespace \
    --set config.pcBase=https://<PC-HOST>:9440/api
```

`config.pcBase` is **required** (must end in `/api`) — the chart refuses to render
without it. Point each RestDefinition OAS slice's `servers[0].url` at the in-cluster
Service the chart prints (e.g.
`http://nutanix-mw.nutanix-system.svc.cluster.local:8080`); use
`fullnameOverride: nutanix-mw` to keep that exact name.

## Apply the RestDefinitions

The generated RestDefinitions live under `generated/`, packaged with a kustomization:

```console
$ kubectl apply -k generated/                    # namespace + 189 ConfigMaps + 189 RestDefinitions
$ kubectl get restdefinitions -n nutanix-system  # READY -> True
$ kubectl get crd | grep nutanix.krateo.io       # the resource + <Kind>Configuration CRDs
```

Applying all 189 spins up 189 controller Deployments — heavy for a small/KIND cluster
(a default node caps at ~110 pods). Apply a subset there (e.g. only the `vmm/` slices you
need for the VirtualMachine blueprint). Once a resource's RestDefinition is `READY`, you
can create instances of its CRD; the minimal shape of any KOG Nutanix resource is:

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

Each KOG kind also needs its own typed `<Kind>Configuration` CR (e.g. `VmConfiguration`,
`SerialPortConfiguration`) that references the credentials Secret.

## Deploy the VirtualMachine blueprint — standalone

Renders the KOG `Vm` plus its `VmConfiguration`:

```console
$ helm template my-vm blueprints/nutanix-virtualmachine \
    --set vm.clusterExtId=<PE-cluster-extId> \
    --set 'disks[0].sizeBytes=21474836480' \
    --set 'nics[0].subnetExtId=<subnet-extId>' | kubectl apply -f -
```

`vm.clusterExtId` is required (a registered Prism Element cluster extId) — the chart
`fail`s without it. Disks, NICs and serial ports are declared inline (see
[configuration](./configuration.md)).

## Deploy the VirtualMachine blueprint — as a Krateo composition

1. Package + publish the chart (its `CompositionDefinition` points at the published
   artifact — see [release](./release.md)):

   ```console
   $ helm dependency build blueprints/nutanix-virtualmachine   # vendor portal-composition-page-generic
   $ helm package blueprints/nutanix-virtualmachine
   $ helm push nutanix-virtualmachine-0.3.0.tgz oci://ghcr.io/krateo-blueprints/charts
   ```

2. Register the blueprint:

   ```console
   $ kubectl apply -f blueprints/nutanix-virtualmachine/compositiondefinition.yaml
   ```

3. Apply a `NutanixVirtualmachine` composition (see
   [examples](./examples.md) and
   `blueprints/nutanix-virtualmachine/examples/composition.yaml`); the
   composition-dynamic-controller renders the same chart. Because the chart depends on
   `portal-composition-page-generic`, a full Krateo install also renders an opinionated
   **Composition page** in the portal (Events, managed-resource Status, a Values form)
   for each `NutanixVirtualmachine`. Verified end-to-end on a live PC: composition →
   `Vm` `Synced=True, Ready=True/Available` with an inline disk + serial port.

## The day-2 chain-lookup demo

`blueprints/nutanix-chain-lookup` couples a dependent `SerialPort` to the parent VM's
runtime `status.extId` via Helm's `lookup`. Simulate the controller's reconcile loop with
repeated `helm upgrade`:

```console
$ helm upgrade --install lk blueprints/nutanix-chain-lookup -n nutanix-system \
    --set configuration.name=nutanix-pc-lk \
    --set vm.clusterExtId=<PE-cluster-extId>
# repeat the upgrade; once the Vm's status.extId is set, the SerialPort renders coupled.
```

This path is experimental until the parent VM reliably publishes `status.extId`
upstream (see [overview](./overview.md)).
