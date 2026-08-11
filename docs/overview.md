---
type: Architecture
title: krateo-nutanix-operator-kog — overview
description: How the pieces fit — RestDefinitions turned into CRDs and controllers by KOG, the translating proxy that lets a schema-agnostic controller speak the Nutanix v4 dialect, and the blueprints that model a VM and a day-2 lookup chain on top.
resource: https://github.com/krateo-blueprints/krateo-nutanix-operator-kog
tags: [nutanix, kog, oasgen-provider, rest-dynamic-controller, proxy, blueprint]
timestamp: 2026-08-11T00:00:00Z
---

# Overview

The goal is to drive **Nutanix Prism Central v4** entirely declaratively: a Nutanix
resource becomes a Kubernetes custom resource, and a controller reconciles the real
thing. Nothing here is a hand-written per-resource controller — everything is generated
from the official OpenAPI specs and translated at runtime.

## The generation pipeline

```
oas/_official/<ns>.yaml   (official Nutanix v4 OpenAPI spec, 19 namespaces)
        │  scripts/generate_restdefinitions.py  (trim + sanitize + map verbs)
        ▼
generated/<ns>/oas/<kind>.yaml            (self-contained OAS slice, < 1 MB)
generated/<ns>/restdefinitions/<kind>.restdefinition.yaml
        │  KOG / oasgen-provider  (restdefinitions.ogen.krateo.io)
        ▼
<kind>.<ns>.nutanix.krateo.io CRD  +  <Kind>Configuration CRD  +  rest-dynamic-controller
        │  the controller reconciles the CR against the v4 REST API
        ▼   (through the proxy)
the real Nutanix resource on Prism Central
```

Each `RestDefinition` maps a resource's verbs onto v4 endpoints — `findby` = GET on the
collection, `create` = POST on the collection, `get`/`update`/`delete` = GET/PUT/DELETE
on `collection/{id}`. `identifiers` prefer `name`; the `{id}` path param is fed from
`status.extId`; OData query params (`$filter`, `$page`, `$limit`, …) are listed in
`excludedSpecFields` so they are not treated as desired state. The generator trims each
resource's paths plus the transitive `$ref` closure of the schemas they touch into a
self-contained, valid OpenAPI 3.0.1 doc small enough to fit a ConfigMap, and strips
Nutanix's `$`-prefixed reserved fields and `default`/`example` values that break CRD
codegen.

There are **189 RestDefinitions** across all 19 Prism Central v4 namespaces. See
`generated/ANALYSIS.md` for the per-resource inventory (verbs, sync/async, slice size)
and `generated/README.md` for how each is produced.

## Why a proxy

The Nutanix v4 API has conventions a schema-agnostic `rest-dynamic-controller` does not
handle on its own. The `nutanix-v4-proxy` (`quickstart/middleware/nutanix_v4_proxy.py`,
stdlib-only Python; packaged as `charts/nutanix-v4-proxy`) sits **between** the
controller and Prism Central and performs runtime translations:

| translation | what the v4 API needs |
|---|---|
| `$objectType` discriminator injection | POST/PUT bodies must carry a Nutanix polymorphic discriminator derived from the request path |
| `NTNX-Request-Id` | an idempotency UUID on POST/PUT/DELETE |
| async **task** resolution | most writes return `202` + a `TaskReference`; the proxy polls the task and returns the real resource as a synchronous `200` (surfacing failures) |
| ETag / `If-Match` | required on PUT/DELETE, and parent `If-Match` on child creates |
| OData `$filter` quoting | `?name=X` becomes `name eq 'X'` |
| optional `X-Cluster-Id` | default cluster extId for cluster-scoped endpoints |
| int-stringify, read-modify-write day-2 updates | large integers and PUT-merge semantics |

RestDefinition OAS slices point their `servers[0].url` at the in-cluster proxy Service,
so the controller talks v4 through it. Three generic codegen fixes are also applied to
each slice by `scripts/patch_slice.py` (expand `4XX`/`5XX` range codes to explicit
`200/201/202`; drop the *required* `NTNX-Request-Id`/`If-Match` params the proxy
injects; add a findby filter param). Both the proxy translations and the slice fixes are
things that ultimately belong upstream in the oasgen-provider templates.

## What the blueprints add

The RestDefinitions give you one CR per Nutanix resource. The blueprints package
**opinionated compositions** of those resources as Krateo blueprints (Helm chart +
`CompositionDefinition`), so a full Krateo install exposes them as native compositions
with a portal page.

- **`blueprints/nutanix-virtualmachine`** provisions a complete AHV VM as a *single* KOG
  `Vm` resource, with disks, NICs and serial ports declared **inline** on the VM. The
  Nutanix v4 `Vm` create body accepts those inline, and the KOG-generated `Vm` CRD
  carries them (disk `backingInfo` is preserved via
  `x-kubernetes-preserve-unknown-fields`, so its `$objectType` discriminator survives),
  so the VM comes up fully built with **no runtime extId wiring**. This is the
  composition-friendly alternative to a parent→child chain. The chart also renders the
  `VmConfiguration` that holds the Prism Central credentials, and depends on
  `portal-composition-page-generic` (Krateo Marketplace) to render a Composition page.
- **`blueprints/nutanix-chain-lookup`** demonstrates the *other* pattern: coupling a
  day-2 child (`SerialPort`) to the parent VM's runtime `status.extId` using Helm's
  `lookup` function. `lookup` reads live cluster state, so it resolves on a later
  reconcile once the parent exists — the composition-dynamic-controller re-renders every
  reconcile, so no manual ordering is needed. It is a demo because it depends on the
  parent reliably publishing `status.extId`, which `rest-dynamic-controller` 0.8.0 does
  not yet keep populated from the cold-create findby-list path — treat that chain as
  experimental.

## Coverage and known limits

Validated against a live `pc.2024.3.1.13`: **89 / 189 RDs proven end-to-end** (30
full-CRUD + 59 read), **182 / 189 routes confirmed live**. The rest are blocked by
undeployed PC services (Files, Licensing, Objects) or features needing external infra
(LDAP/SAML, AWS cloud connectivity). Three resources fail oasgen's CRD codegen
(`clustermgmt/clusterprofile`, `clustermgmt/trap`, `vmm/version`) — an oasgen/crdgen
limitation on Nutanix's `Version` type, not the slice content. See `GA_V4_FULL_CRUD.md`
and `LIVE_TEST_MATRIX.md` for the per-RD verdicts.

## Operational note

The Nutanix v4 conventions imply an operational rule documented in the quickstarts:
**serialize controllers** — a concurrent write storm can lock the shared PC admin
account. Applying all 189 RestDefinitions also spins up 189 controller Deployments,
which is heavy for a small or KIND cluster (a default node caps at ~110 pods); apply a
subset there.
