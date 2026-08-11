---
type: ExampleIndex
title: krateo-nutanix-operator-kog — examples
description: Index of the runnable examples for the Nutanix KOG charts.
resource: https://github.com/krateo-blueprints/krateo-nutanix-operator-kog
tags: [examples, nutanix, blueprint, composition]
timestamp: 2026-08-11T00:00:00Z
---

# Examples

- [examples/nutanix-virtualmachine](../examples/nutanix-virtualmachine/README.md) —
  provision a complete Nutanix AHV VM (disks, NICs and serial ports declared inline) as a
  single KOG `Vm` resource via the `nutanix-virtualmachine` blueprint, either standalone
  (`helm template … | kubectl apply`) or as a `NutanixVirtualmachine` Krateo composition.

## More examples in the repo

- `blueprints/nutanix-virtualmachine/examples/composition.yaml` — the in-chart copy of the
  composition manifest, shipped alongside the blueprint.
- `blueprints/nutanix-chain-lookup/` — the day-2 lookup-coupling demo (couples a
  `SerialPort` to the parent VM's runtime `status.extId`); run it with repeated
  `helm upgrade` (see [usage](./usage.md)).
- `quickstart/` — operator quickstarts against a live Prism Central: `category/`,
  `volumegroup/`, `addressgroup/`, and the full VM walkthrough in `quickstart/README.md`.
