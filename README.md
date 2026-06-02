# Krateo RestDefinitions for Nutanix Prism Central v4

Manage Nutanix Prism Central resources as native Kubernetes objects, using the
**Krateo Operator Generator (KOG / `oasgen-provider`)**. Each `RestDefinition`
points at a trimmed OpenAPI slice and tells the provider how to map CRUD to the
Nutanix v4 REST endpoints; the provider then generates a CRD + controller
(`rest-dynamic-controller`) that reconciles the external resource.

Covered resources (first set):

| Resource | Namespace | Group | Verbs |
|---|---|---|---|
| `VirtualMachine` | vmm | `vmm.nutanix.krateo.io` | findby, create, get, update, delete |
| `Image` | vmm | `vmm.nutanix.krateo.io` | findby, create, get, update, delete |
| `Subnet` | networking | `networking.nutanix.krateo.io` | findby, create, get, update, delete |
| `Cluster` | clustermgmt | `clustermgmt.nutanix.krateo.io` | findby, get, update (read-oriented) |
| `Category` | prism | `prism.nutanix.krateo.io` | findby, create, get, update, delete |

> **Start with `Category`** — it is synchronous full-CRUD and is the cleanest
> first end-to-end test of the whole toolchain.

## Layout

```
oas/                         # trimmed, oasgen-friendly OpenAPI slices (one per resource)
  vmm/{vm,image}.yaml
  networking/subnet.yaml
  clustermgmt/cluster.yaml
  prism/category.yaml
  _raw/                      # (created by pull-specs.sh) authoritative specs from a live PC
kustomization.yaml           # repo root: namespace + OAS ConfigMaps + RestDefinitions
manifests/
  00-namespace.yaml
  restdefinitions/*.yaml     # one RestDefinition per resource
  config/                    # Secret + Configuration TEMPLATES (edit before use)
  examples/                  # sample instances of the generated CRDs
mock/                        # dependency-free mock Nutanix v4 API for local testing
  mock_server.py
  deploy.yaml                # Deployment + Service
  kustomization.yaml         # kubectl apply -k mock/
scripts/
  make-configmaps.sh         # build the OAS ConfigMaps (alternative to kustomize)
  pull-specs.sh              # pull real specs from a live Prism Central
```

## Prerequisites

1. A Kubernetes cluster with **Krateo PlatformOps** and the **oasgen-provider**
   installed. See https://docs.krateo.io/key-concepts/kog/oasgen-provider/ .
2. Network reachability + credentials for a Prism Central (see below for a free one).

## Quick start

```bash
# 1. Namespace + OAS ConfigMaps + RestDefinitions (run from repo root)
kubectl apply -k .

# 2. Wait for the provider to generate the CRDs + controllers
kubectl get restdefinitions -n nutanix-system
kubectl get crds | grep nutanix.krateo.io

# 3. Credentials + Configuration (EDIT these templates first)
kubectl -n nutanix-system create secret generic nutanix-pc-credentials \
  --from-literal=username='admin' --from-literal=password='YOUR_PW'
#   ...or --from-literal=apiKey='YOUR_KEY'
kubectl apply -f manifests/config/category-configuration.example.yaml

# 4. Create a resource
kubectl apply -f manifests/examples/category.example.yaml
kubectl get category -n nutanix-system -o wide
```

The generated `Configuration` schema is whatever the provider derived from the
OAS `securitySchemes` + `servers`. After step 2, inspect the real shape and
adjust the templates in `manifests/config/`:

```bash
kubectl explain categoryconfiguration.prism.nutanix.krateo.io --recursive
```

## Getting a free, functional Prism Central

The Nutanix v4 specs are **not published as downloadable files** — a running
Prism Central is the authoritative source (and your test target).

- **Nutanix Community Edition (CE)** — free, full AOS/AHV + deployable Prism
  Central; download from the Nutanix portal (free account). Run nested
  (VMware Workstation/Fusion/ESXi) or on bare metal. **Use a recent build
  (CE 2024.x / pc.2024.x+)** where the v4 APIs are GA. Needs a host with
  ~32 GB+ RAM and an SSD. This is the recommended option.
- **Nutanix Test Drive** — free hosted, time-boxed sandbox; quick but ephemeral
  and with limited API access.

Once it is up, pull the real specs:

```bash
PC_HOST=10.0.0.10:9440 PC_USER=admin PC_PASS='secret' ./scripts/pull-specs.sh
# -> oas/_raw/<namespace>-<version>.json
```

Then trim each raw spec down to the resource + verbs you need, replacing the
hand-authored slices under `oas/<namespace>/`.

## Testing against the mock (no Prism Central required)

Nutanix **Test Drive does not allow REST API calls**, so it can't be used here.
Instead, a dependency-free **mock v4 API** (`mock/`) reproduces the awkward parts
of the real API — `{"data": ...}` envelope, `202` + task for async resources,
`ETag`/`If-Match` and `Ntnx-Request-Id` enforcement — so you can validate the
RestDefinitions end-to-end locally, then point at a real PC by changing only the
Configuration `server` variables.

```bash
# Deploy the mock into the cluster
kubectl apply -k mock/
kubectl -n nutanix-system rollout status deploy/nutanix-mock

# RestDefinitions + OAS ConfigMaps (if not already applied)
kubectl apply -k .

# Credentials (mock accepts anything) + mock-targeted Configuration (scheme=http)
kubectl -n nutanix-system create secret generic nutanix-pc-credentials \
  --from-literal=username=admin --from-literal=password=mock
kubectl apply -f manifests/config/category-configuration.mock.yaml

# Drive a resource and watch it reconcile
kubectl apply -f manifests/examples/category.example.yaml
kubectl get category -n nutanix-system -o wide
```

Quick local smoke test of the mock without Kubernetes:

```bash
PORT=18080 python3 mock/mock_server.py &
curl -s -X POST localhost:18080/api/prism/v4.0/config/categories \
  -d '{"key":"environment","value":"production"}'        # -> 200 {"data":{...,"extId":...}}
curl -s -X POST localhost:18080/api/vmm/v4.1/ahv/config/vms \
  -d '{"name":"demo-vm"}'                                  # -> 202 {"data":{"extId":"<taskId>"}}
```

When a real Prism Central is available, switch the Configuration from
`category-configuration.mock.yaml` (scheme=http, mock Service) to
`category-configuration.example.yaml` (scheme=https, PC host) — no other changes.

## Architectural caveats (important)

The Nutanix v4 APIs do **not** fit oasgen-provider's synchronous REST model
perfectly. The scaffold maps the endpoints correctly, but these gaps remain and
are deferred (no wrapper yet):

1. **Async tasks.** `POST`/`PUT`/`DELETE` return `202` + a *TaskReference*, not
   the entity. The real outcome must be polled from the `prism` task API. The
   `findby` action (match on `name` / `key+value`) lets the controller discover
   the entity and its `extId` after the task completes, but the controller does
   **not** poll the task itself. Until a wrapper is added, expect a reconcile
   lag while the async op finishes, and verify completion out-of-band.

2. **ETag concurrency.** `PUT`/`DELETE` require the current entity's `ETag` in an
   `If-Match` header **plus** a unique UUID in `Ntnx-Request-Id`. These are
   declared as header parameters in the OAS slices, but oasgen does not natively
   capture an ETag from a prior `GET` and replay it. This typically needs a thin
   wrapper service (the documented escape hatch) that:
   - issues the `GET`, captures the `ETag`,
   - generates a `Ntnx-Request-Id`,
   - replays the mutating call with both headers,
   - and (optionally) blocks until the task completes — turning the async+ETag
     dance into a clean synchronous REST call oasgen consumes directly.

3. **Response envelope.** v4 responses wrap the entity in `{"data": ...}`. The
   slices model this; `identifiers`/`additionalStatusFields` assume the
   controller reads `extId`. If your provider build does not auto-unwrap `data`,
   change those field paths to `data.extId` (and adjust `requestFieldMapping`).

A production-correct next step is to design the wrapper from caveats 1–2 (chosen
to defer for now). The RestDefinitions are written so that swapping the
`servers.url` to point at such a wrapper is the only change needed.

## How the mapping works (recap)

- `spec.oasPath: configmap://<ns>/<cm>/<file>` — the OAS slice, mounted as a ConfigMap.
- `resource.identifiers` — fields used by `findby` to locate the entity (Nutanix
  has no synchronous id-on-create, so we match on `name` / `key+value`).
- `resource.additionalStatusFields` — extra fields surfaced in `.status` (here
  `extId`, the Nutanix external id).
- `verbsDescription[].requestFieldMapping` — feeds `status.extId` back into the
  `{extId}` path parameter for `get`/`update`/`delete`.

## References

- Krateo OASGen Provider — https://docs.krateo.io/key-concepts/kog/oasgen-provider/
- KOG cheatsheet — https://docs.krateo.io/key-concepts/kog/oasgen-provider-cheatsheet/
- Real examples — https://github.com/krateoplatformops/oasgen-provider/blob/main/docs/REAL_EXAMPLES.md
- Nutanix v4 API user guide — https://www.nutanix.dev/nutanix-api-user-guide/
- ETag / If-Match — https://www.nutanix.dev/2022/12/01/using-etag-and-if-match-headers-with-nutanix-v4-apis/
