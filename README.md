<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/hero-dark.svg">
    <img alt="Krateo ❤ Nutanix" src="docs/hero-light.svg" width="820">
  </picture>
</p>

# Krateo RestDefinitions for Nutanix Prism Central v4

Manage **Nutanix Prism Central (GA v4.0)** resources as native Kubernetes objects with
**Krateo** and the **Operator Generator (KOG / `oasgen-provider`)**. Each `RestDefinition`
points at an OpenAPI slice and maps the resource's verbs onto the Nutanix v4 REST API;
KOG then generates a CRD + a `rest-dynamic-controller` that reconciles the real resource —
**no per-resource controller code**.

This repo contains:

- **189 RestDefinitions** across all 19 Nutanix v4 namespaces (`generated/`), generated 1:1
  from the official OpenAPI specs (`oas/_official/`).
- A small, resource-agnostic **Nutanix v4 proxy** that lets the generic controller speak the
  v4 dialect (`quickstart/middleware/`).
- **Operator quickstarts** that create real resources on a live PC (`quickstart/`).
- A **per-RD live-test matrix** and an API-level validation report.

## Why a proxy?

The Nutanix v4 API has conventions a generic OpenAPI controller doesn't handle. The proxy
([`quickstart/middleware/nutanix_v4_proxy.py`](quickstart/middleware/nutanix_v4_proxy.py),
stdlib-only) sits between the controller and Prism Central and performs five runtime
translations — it injects the `$objectType` discriminator (derived from the request path),
adds the `NTNX-Request-Id` idempotency header, resolves the async `202 → task → resource`
flow into a synchronous `200`, handles `If-Match` ETags, and quotes OData `$filter` values.

Each RD's OpenAPI slice also needs three generic codegen fixes (applied by
[`scripts/patch_slice.py`](scripts/patch_slice.py)): expand range response codes
(`4XX`/`5XX` → explicit) and add `200/201/202`; drop the *required* `NTNX-Request-Id`/`If-Match`
params (the proxy injects them); add a findby filter param. These belong upstream in the
oasgen-provider templates.

## Quickstarts

Start with **`Category`** (synchronous, no parent — the cleanest end-to-end test):

- [`quickstart/README.md`](quickstart/README.md) — **VM**, the full walkthrough (with Prism UI screenshots)
- [`quickstart/category/`](quickstart/category) — Category (sync)
- [`quickstart/volumegroup/`](quickstart/volumegroup) — VolumeGroup (async)
- [`quickstart/addressgroup/`](quickstart/addressgroup) — AddressGroup (async)

The minimal shape of every quickstart resource:

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
  # ... resource fields (see each quickstart)
```

## Layout

```
generated/                 # 189 RestDefinitions + their OAS slices, by namespace
  <ns>/restdefinitions/*.restdefinition.yaml
  <ns>/oas/*.yaml
  README.md  ANALYSIS.md     # inventory of every resource (verbs, sync/async)
oas/_official/             # official Nutanix v4 OpenAPI specs (19 namespaces)
quickstart/                # operator quickstarts (VM, Category, VolumeGroup, AddressGroup)
  middleware/              # the Nutanix v4 proxy (code, Dockerfile, deploy.yaml)
scripts/
  patch_slice.py           # apply the 3 generic slice-fixes to any OAS slice
  live_test.py             # serialized live-tester for read-observe RDs
  generate_restdefinitions.py
LIVE_TEST_MATRIX.md        # per-RD: how each can be live-tested (or why it's blocked)
GA_V4_FULL_CRUD.md         # API-level validation of all 189 RDs against a live PC
```

## Coverage

Validated against a live `pc.2024.3.1.13`: **89 / 189 RDs proven end-to-end**
(30 full-CRUD + 59 read), **182 / 189 routes confirmed live**. See
[`GA_V4_FULL_CRUD.md`](GA_V4_FULL_CRUD.md) for the per-RD verdicts and
[`LIVE_TEST_MATRIX.md`](LIVE_TEST_MATRIX.md) for the per-RD live-test method.
The rest are blocked by undeployed PC services (Files, Licensing, Objects, Atlas
networking) or features absent on a Community-Edition / x-small PC.

> The Nutanix v4 conventions and operational notes (e.g. serialize controllers — a concurrent
> storm can lock the shared PC admin account) are documented in the quickstarts.
