---
type: Log
title: krateo-nutanix-operator-kog — log
description: Curated chronological history of krateo-nutanix-operator-kog — notable changes and decisions, not a generated changelog.
resource: https://github.com/krateo-blueprints/krateo-nutanix-operator-kog
tags: [log, history, nutanix]
timestamp: 2026-08-11T00:00:00Z
---

# Log

Curated history; release notes live in GitHub Releases.

## 2026-08-11 — Documentation Standard adoption

The repo adopts the Krateo Documentation Standard (OKF): the invariant `docs/` bundle
(`index`/`overview`/`usage`/`configuration`/`api`/`examples`/`release`/`log` +
`llms.txt`), a runnable `examples/nutanix-virtualmachine`, a rewritten `README.md` with
the standard six sections, and the shared `lint-docs` check wired into `lint.yaml`.
`index.md` is typed `ChartRepo` because the repo ships a chart family (the v4 proxy chart
plus the VirtualMachine and chain-lookup blueprints).

## 2026-06-11 — Small-PC rebuild unlocked Atlas / Flow Virtual Networking

The PC was rebuilt to size Small with CMSP and the Network Controller (Atlas) enabled and
the PE registered. Re-probed: **17 / 30 `networking` RDs route-reachable (HTTP 200)** — up
from 9 — including `vpc2`, `subnet2`, `floatingip`, `gateway`, `routingpolicy`,
`vpnconnection`, `bgpsession`, `layer2stretch`, and more. Write-CRUD proven through the
operator on Atlas (a `vpc2` create→delete round-trip plus a 5-RD Atlas CRUD sweep). The
`N — Atlas` verdicts in `LIVE_TEST_MATRIX.md` are superseded for the Flow-VN tier.

## Coverage baseline — `pc.2024.3.1.13`

**89 / 189 RDs proven end-to-end** (30 full-CRUD + 59 read), **182 / 189 routes confirmed
live**. The rest are blocked by undeployed PC services (Files, Licensing, Objects) or
features that need external infra (LDAP/SAML, AWS cloud connectivity). See
`GA_V4_FULL_CRUD.md` for the per-RD verdicts and `LIVE_TEST_MATRIX.md` for the per-RD
live-test method.

## Foundations

- **189 RestDefinitions** generated 1:1 from the official Nutanix v4 OpenAPI specs across
  all 19 Prism Central namespaces; **186 / 189** reconcile cleanly (`Synced=True`) on a
  live `oasgen-provider`. Three fail oasgen's CRD codegen (`clustermgmt/clusterprofile`,
  `clustermgmt/trap`, `vmm/version`) on Nutanix's `Version` type — an upstream
  oasgen/crdgen limitation.
- **`nutanix-v4-proxy`** — the stdlib-only translating proxy that lets a schema-agnostic
  `rest-dynamic-controller` drive the v4 API ($objectType injection, async task
  resolution, ETag/If-Match, OData quoting, optional `X-Cluster-Id`). Hardened by default;
  `config.pcBase` is mandatory.
- **`nutanix-virtualmachine`** blueprint — a full AHV VM (disks/NICs/serial ports inline)
  as a single KOG `Vm`; verified end-to-end on a live PC (`Synced=True, Ready=True`).
  Requires proxy ≥ v0.4.0 for `Ready=True`. Renders a Krateo portal Composition page via
  `portal-composition-page-generic`.
- **`nutanix-chain-lookup`** demo — couples a day-2 `SerialPort` to the parent VM's
  runtime `status.extId` via Helm `lookup`; experimental until the parent VM reliably
  publishes `status.extId` upstream.
