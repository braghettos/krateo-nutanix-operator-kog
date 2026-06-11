# Additional product RestDefinitions

Beyond the core **Prism Central GA v4.0** surface (the 19 `v4` namespaces validated in
[`../LIVE_TEST_MATRIX.md`](../LIVE_TEST_MATRIX.md) and [`../GA_V4_FULL_CRUD.md`](../GA_V4_FULL_CRUD.md)),
`scripts/generate_restdefinitions.py` was run against the OpenAPI specs of other Nutanix
products. The generated RestDefinitions live here for reference.

| Dir | Product | API | RDs |
|---|---|---|---:|
| `ndb/` | Nutanix Database Service (Era) | v0.9 | 105 |
| `nke/` | Nutanix Kubernetes Engine (Karbon) | v1 | 46 |
| `foundation/` | Foundation | v1 | 48 |
| `foundationcentral/` | Foundation Central | v1 | 17 |
| `move/` | Move | v2 | 80 |
| `selfservice/` | Self-Service (Calm) | v3 | 288 |
| `nc2/` | NC2 (Nutanix Cloud Clusters) | v1 | 34 |
| `prismv3/` | Prism Central v3 | v3 | 125 |
| `prismv2/` | Prism Element v2 | v2 | 233 |
| | | **total** | **976** |

> **Status: experimental / generated, not end-to-end validated.** These are *not* part of
> the validated 189-RD v4 GA count, and are intentionally **not** wired into the root
> [`kustomization.yaml`](kustomization.yaml) (apply them individually). A 7-product spot
> check found a mix of `Ready` and not-`Ready` RDs (e.g. NDB/NKE produced several `Ready`
> CRDs; Self-Service / Prism v2 mostly did not). The OAS slices use a `pc-host-ip`
> placeholder server — point them at your endpoint before use. Each product's auth/versioning
> may differ from v4 (e.g. v3/v2 paths, `X-Auth-Token` vs basic auth).
