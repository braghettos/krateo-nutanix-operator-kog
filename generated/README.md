# Generated Krateo RestDefinitions — Nutanix v4 (1:1)

Auto-generated, **1:1 Krateo `RestDefinition`s for the full Nutanix Prism Central
v4 API surface** — one resource → one RestDefinition (→ one CRD + controller).

- **Source specs:** the official Nutanix v4 OpenAPI specs in [`../oas/_official/`](../oas/_official) (19 namespaces, pulled from `https://developers.nutanix.com/api/v1/namespaces/{ns}/versions/{ver}/yaml`).
- **Generator:** [`../scripts/generate_restdefinitions.py`](../scripts/generate_restdefinitions.py)
- **Inventory/report:** [`ANALYSIS.md`](ANALYSIS.md) — every resource, its verbs, sync/async, slice size.
- **189 resources** across all 19 namespaces.

## Layout

```
generated/
  00-namespace.yaml                       # nutanix-system namespace
  kustomization.yaml                      # namespace + all ConfigMaps + all RestDefinitions
  ANALYSIS.md                             # resource inventory
  <namespace>/
    oas/<kind>.yaml                       # trimmed OAS slice (this resource only)
    restdefinitions/<kind>.restdefinition.yaml
```

## How each resource is produced

For every CRUD/list resource the generator emits:

1. **A trimmed OAS slice** (`<ns>/oas/<kind>.yaml`) — only that resource's paths
   (`/…/<collection>` and `/…/<collection>/{id}`) plus the **transitive `$ref`
   closure** of every schema they touch. This keeps each slice **< 1 MB** so it
   fits a Kubernetes ConfigMap (the full vmm spec alone is 2.3 MB). Each slice is
   a self-contained, valid OpenAPI 3.0.1 document.
2. **A RestDefinition** mapping CRUD to the endpoints:
   | Krateo action | HTTP |
   |---|---|
   | `findby` | `GET` collection |
   | `create` | `POST` collection |
   | `get` / `update` / `delete` | `GET` / `PUT` / `DELETE` collection/{id} |
   - `identifiers`: `name` when the create body exposes it, else `extId`.
   - `additionalStatusFields: [extId]`; path `{id}` fed from `status.extId` via
     `requestFieldMapping` (parent ids for nested resources → `spec.<param>`).
   - `excludedSpecFields`: OData/list query params (`$filter`, `$page`, `$limit`,
     `$orderby`, `$select`) are dropped — they aren't desired-state.

## Apply

Prereqs: a cluster with **Krateo + `oasgen-provider`** (provides
`restdefinitions.ogen.krateo.io`).

```bash
kubectl apply -k generated/          # namespace + 189 ConfigMaps + 189 RestDefinitions
kubectl get restdefinitions -n nutanix-system            # watch READY flip to True
kubectl get crd | grep nutanix.krateo.io                 # generated CRDs (resource + Configuration)
```

Then create credentials + a `Configuration` per namespace/resource (server URL +
auth), and create resource CRs. See the top-level repo `README.md` / `manifests/`
for Configuration + Secret templates.

> **Heads-up — applying all 189 spins up 189 controller Deployments.** That's heavy
> for a small/KIND cluster; expect pods to come up gradually (or stay `Pending` if
> the node lacks capacity). Apply a subset for small clusters.

## Validated on real infrastructure

Applied to a live Krateo cluster (`kind-nova-kog`, `oasgen-provider` running):
oasgen parsed the slices and generated the **resource CRD + `*Configuration` CRD +
controller** for each, reconciling to `READY=True`, with full schema fidelity
(e.g. the `Vm` CRD carries `name`, `numSockets`, `memorySizeBytes`, `disks[]`,
`nics[]`, `cluster`, `bootConfig`…). Query params are correctly excluded.

## Caveats

- **`identifiers` are immutable** once a CRD is generated. To change them you must
  **delete and recreate** the RestDefinition (oasgen rejects the in-place update).
- **Most v4 write ops are async** (`202` + a TaskReference) and `PUT`/`DELETE`
  require an `If-Match` ETag + `Ntnx-Request-Id` header. The generated mappings
  describe the endpoints faithfully, but real create/update/delete round-trips
  need task-polling + ETag replay (a thin wrapper service, or controller support).
  See `ANALYSIS.md` for which resources are async.
- **Polymorphic `$objectType` discriminators:** the slice keeps every explicit
  `$ref`; if a spec maps subtypes by name only, widen the closure in the generator.
- These are **generated** — review before production use; regenerate with
  `python3 scripts/generate_restdefinitions.py`.
