---
type: ChartRepo
title: krateo-nutanix-operator-kog — index
description: The map of the krateo-nutanix-operator-kog doc bundle — a family of Krateo charts (KOG RestDefinitions, VirtualMachine blueprint, chain-lookup demo, v4 translating proxy) that manage Nutanix Prism Central v4 resources as native Kubernetes objects.
resource: https://github.com/krateo-blueprints/krateo-nutanix-operator-kog
tags: [nutanix, prism-central, kog, oasgen-provider, blueprint, restdefinition, chartrepo]
timestamp: 2026-08-11T00:00:00Z
---

# krateo-nutanix-operator-kog

This repo lets you manage **Nutanix Prism Central (GA v4.0)** resources as native
Kubernetes objects with **Krateo** and the **Operator Generator** (KOG /
`oasgen-provider`). It ships a *family* of related charts and generated assets rather
than a single deliverable:

- **189 `RestDefinition`s** (`generated/`) — one per Nutanix v4 resource, across all 19
  Prism Central v4 namespaces (`vmm`, `networking`, `clustermgmt`, `iam`, …). Each maps
  a resource's verbs onto the v4 REST API; KOG turns each into a CRD plus a
  `rest-dynamic-controller` that reconciles the real resource — no per-resource
  controller code.
- **`charts/nutanix-v4-proxy`** — a small, resource-agnostic translating proxy that lets
  the generic controller speak the v4 dialect ($objectType discriminator, async task
  resolution, ETag/If-Match, OData `$filter` quoting).
- **`blueprints/nutanix-virtualmachine`** — a Krateo blueprint (Helm chart +
  `CompositionDefinition`) that provisions a complete AHV virtual machine (disks, NICs,
  serial ports declared inline) as a single KOG `Vm` resource, and renders an
  opinionated Composition page in the Krateo portal.
- **`blueprints/nutanix-chain-lookup`** — a demo blueprint that couples a day-2 child
  KOG resource to a parent's runtime `status.extId` via Helm's `lookup`.

## The bundle (start here)

- [overview](./overview.md) — how the pieces fit: RestDefinitions → KOG → CRD +
  controller, why a proxy is needed, and what the blueprints add on top.
- [usage](./usage.md) — prerequisites, applying the RestDefinitions, installing the
  proxy, deploying the VirtualMachine blueprint standalone or as a Krateo composition.
- [configuration](./configuration.md) — the values of every chart, the proxy env, and
  the RestDefinition mapping conventions.
- [api](./api.md) — the CRDs this repo produces: the KOG-generated resource CRDs
  (`Vm`, `VmConfiguration`, …) and the `CompositionDefinition` the VirtualMachine
  blueprint registers.
- [examples](./examples.md) — the runnable examples under `examples/`.
- [release](./release.md) — how the proxy image + chart and the blueprint chart ship.
- [log](./log.md) — curated history.
- [llms.txt](./llms.txt) — the doc index of this bundle.

## Layout

```
generated/                 # 189 RestDefinitions + their trimmed OAS slices, by namespace
  <ns>/restdefinitions/*.restdefinition.yaml
  <ns>/oas/*.yaml
  README.md  ANALYSIS.md    # inventory of every resource (verbs, sync/async, slice size)
oas/_official/             # official Nutanix v4 OpenAPI specs (19 namespaces)
charts/
  nutanix-v4-proxy/        # the v4 translating proxy Helm chart
blueprints/
  nutanix-virtualmachine/  # the VM blueprint (chart + compositiondefinition.yaml)
  nutanix-chain-lookup/    # the day-2 lookup-coupling demo blueprint
quickstart/                # operator quickstarts (VM, Category, VolumeGroup, AddressGroup)
  middleware/              # the proxy source (nutanix_v4_proxy.py, Dockerfile, deploy.yaml)
scripts/                   # generate_restdefinitions.py, patch_slice.py, live_test.py
```
