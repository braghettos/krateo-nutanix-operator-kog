#!/usr/bin/env python3
"""Generate 1:1 Krateo RestDefinitions from the official Nutanix v4 OpenAPI specs.

For every CRUD-capable (or list/get) resource in each spec under oas/_official/,
emit:
  generated/<ns>/oas/<kind>.yaml            - a trimmed OAS slice (paths +
                                              transitive $ref closure, <1MB so it
                                              fits a ConfigMap)
  generated/<ns>/restdefinitions/<kind>.yaml - the RestDefinition mapping CRUD to
                                              the resource's endpoints
  generated/kustomization.yaml              - namespace + ConfigMaps + RestDefinitions
  generated/ANALYSIS.md                     - the resource inventory / report

Krateo verb mapping:
  findby -> GET  collection      create -> POST collection
  get    -> GET  collection/{id} update -> PUT  collection/{id}
  delete -> DELETE collection/{id}
The resource's own id path-param is fed from status.extId via requestFieldMapping;
parent path-params (nested resources) are mapped from spec.<param> (flagged TODO).
"""
import glob
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SPEC_DIR = os.path.join(ROOT, "oas", "_official")
OUT = os.path.join(ROOT, "generated")
NS_GROUP = "{ns}.nutanix.krateo.io"

# ---- helpers ---------------------------------------------------------------

def camel(s):
    return "".join(p[:1].upper() + p[1:] for p in re.split(r"[-_ ]", s) if p)


def singular(seg):
    s = camel(seg)
    if s.endswith("ies"):
        return s[:-3] + "y"
    if s.endswith("sses") or s.endswith("ches") or s.endswith("shes"):
        return s[:-2]
    if s.endswith("s") and not s.endswith("ss"):
        return s[:-1]
    return s


def last_param(path):
    m = re.findall(r"\{([^}]+)\}", path)
    return m[-1] if m else None


def collection_of(path):
    return re.sub(r"/\{[^/}]+\}$", "", path)


def collect_refs(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "$ref" and isinstance(v, str):
                acc.add(v)
            else:
                collect_refs(v, acc)
    elif isinstance(obj, list):
        for x in obj:
            collect_refs(x, acc)


def trimmed_spec(spec, paths_subset):
    """Build a minimal valid OAS with only paths_subset + transitively-referenced
    components."""
    comps = spec.get("components", {}) or {}
    frontier = set()
    for p in paths_subset.values():
        collect_refs(p, frontier)
    # also seed from shared security schemes (kept wholesale, they're tiny)
    kept = {sec: set() for sec in comps}
    seen = set()
    while frontier:
        ref = frontier.pop()
        if ref in seen or not ref.startswith("#/components/"):
            seen.add(ref)
            continue
        seen.add(ref)
        parts = ref.split("/")
        sec, name = parts[-2], parts[-1]
        if sec in comps and name in comps.get(sec, {}):
            kept.setdefault(sec, set()).add(name)
            sub = set()
            collect_refs(comps[sec][name], sub)
            frontier |= (sub - seen)
    out_comps = {}
    for sec, names in kept.items():
        if sec == "securitySchemes":
            out_comps[sec] = comps[sec]  # keep all (tiny)
        elif names:
            out_comps[sec] = {n: comps[sec][n] for n in names if n in comps[sec]}
    if "securitySchemes" in comps and "securitySchemes" not in out_comps:
        out_comps["securitySchemes"] = comps["securitySchemes"]
    return {
        "openapi": spec.get("openapi", "3.0.1"),
        "info": spec.get("info", {"title": "trimmed", "version": "4.0"}),
        "servers": spec.get("servers", []),
        "security": spec.get("security", []),
        "paths": paths_subset,
        "components": out_comps,
    }


def schema_props(spec, sch, depth=0):
    """Resolve a schema's property names through $ref and allOf."""
    if depth > 6 or not isinstance(sch, dict):
        return set()
    if "$ref" in sch:
        name = sch["$ref"].split("/")[-1]
        return schema_props(spec, spec.get("components", {}).get("schemas", {}).get(name, {}), depth + 1)
    props = set((sch.get("properties", {}) or {}).keys())
    for sub in (sch.get("allOf", []) or []):
        props |= schema_props(spec, sub, depth + 1)
    return props


def request_has_field(spec, op, field):
    """Heuristic: does the create request body schema expose `field`?"""
    try:
        content = op["requestBody"]["content"]
        sch = next(iter(content.values()))["schema"]
        return field in schema_props(spec, sch)
    except Exception:
        return False


def query_param_names(spec, op):
    """Query-parameter names of an operation (resolving $ref params)."""
    names = set()
    for p in (op.get("parameters", []) or []):
        if isinstance(p, dict) and "$ref" in p:
            nm = p["$ref"].split("/")[-1]
            p = spec.get("components", {}).get("parameters", {}).get(nm, {})
        if isinstance(p, dict) and p.get("in") == "query" and p.get("name"):
            names.add(p["name"])
    return names


# ---- generation ------------------------------------------------------------

def main():
    report = ["# Nutanix v4 API — resource inventory & generated RestDefinitions\n"]
    total_rd = 0
    km_resources = []
    km_configmaps = []

    for f in sorted(glob.glob(os.path.join(SPEC_DIR, "*.yaml"))):
        base = os.path.basename(f).rsplit(".", 1)[0]   # e.g. vmm-v4.0
        ns = base.rsplit("-", 1)[0]
        spec = yaml.safe_load(open(f))
        paths = spec.get("paths", {})
        ver_seg = None  # discovered from first path

        # group: collection -> {"collection": path, "item": path|None, "ops": {...}}
        groups = {}
        for path, item in paths.items():
            if "$actions" in path or "/stats/" in path:
                continue  # action/stat endpoints aren't CRUD resources
            coll = collection_of(path)
            g = groups.setdefault(coll, {"collection": None, "item": None})
            if path == coll:
                g["collection"] = path
            elif re.match(re.escape(coll) + r"/\{[^/}]+\}$", path):
                g["item"] = path

        ns_dir = os.path.join(OUT, ns)
        rd_dir = os.path.join(ns_dir, "restdefinitions")
        oas_dir = os.path.join(ns_dir, "oas")
        emitted = []
        used_kinds = set()
        for coll, g in sorted(groups.items()):
            cpath, ipath = g["collection"], g["item"]
            if not cpath and not ipath:
                continue
            cops = paths.get(cpath, {}) if cpath else {}
            iops = paths.get(ipath, {}) if ipath else {}
            verbs = []
            if cpath and "get" in cops:
                verbs.append(("findby", "GET", cpath))
            if cpath and "post" in cops:
                verbs.append(("create", "POST", cpath))
            if ipath and "get" in iops:
                verbs.append(("get", "GET", ipath))
            if ipath and "put" in iops:
                verbs.append(("update", "PUT", ipath))
            if ipath and "delete" in iops:
                verbs.append(("delete", "DELETE", ipath))
            if not verbs:
                continue
            seg = coll.rstrip("/").split("/")[-1]
            if seg.startswith("{"):
                continue
            kind = singular(seg)
            if not kind or not kind[0].isalpha():
                continue
            # disambiguate kind collisions within the namespace (e.g. ahv vs esxi vms)
            if kind in used_kinds:
                segs = coll.strip("/").split("/")
                mids = [s for s in segs[2:-1] if s != "config" and not s.startswith("{")]
                qual = camel(mids[0]) if mids else ""
                cand = (qual + kind) if qual else kind
                base, i = cand, 2
                while cand in used_kinds:
                    cand = f"{base}{i}"; i += 1
                kind = cand
            used_kinds.add(kind)
            # build trimmed slice
            subset = {}
            if cpath:
                subset[cpath] = paths[cpath]
            if ipath:
                subset[ipath] = paths[ipath]
            slice_spec = trimmed_spec(spec, subset)
            # identifiers: prefer name if present in create body
            create_op = cops.get("post")
            id_field = "name" if (create_op and request_has_field(spec, create_op, "name")) else None
            identifiers = [id_field] if id_field else ["extId"]
            # async?
            is_async = "202" in str({**cops, **iops}) or "TaskReference" in str({**cops, **iops})

            # verbsDescription with requestFieldMapping for path params
            vds = []
            id_param = last_param(ipath) if ipath else None
            for action, method, p in verbs:
                vd = {"action": action, "method": method, "path": p}
                params = re.findall(r"\{([^}]+)\}", p)
                if params:
                    rfm = []
                    for prm in params:
                        if prm == id_param:
                            rfm.append({"inPath": prm, "inCustomResource": "status.extId"})
                        else:
                            rfm.append({"inPath": prm, "inCustomResource": "spec." + prm})
                    vd["requestFieldMapping"] = rfm
                vds.append(vd)

            # query params (filter/page/limit/$orderby/...) aren't desired-state -> exclude
            excluded = set()
            for _a, _m, _p in verbs:
                excluded |= query_param_names(spec, paths[_p].get(_m.lower(), {}))
            cm_name = f"nutanix-{ns}-{kind.lower()}-oas"
            rd = {
                "apiVersion": "ogen.krateo.io/v1alpha1",
                "kind": "RestDefinition",
                "metadata": {"name": f"nutanix-{ns}-{kind.lower()}", "namespace": "nutanix-system"},
                "spec": {
                    "oasPath": f"configmap://nutanix-system/{cm_name}/{kind.lower()}.yaml",
                    "resourceGroup": NS_GROUP.format(ns=ns),
                    "resource": {
                        "kind": kind,
                        "identifiers": identifiers,
                        "additionalStatusFields": ["extId"],
                        **({"excludedSpecFields": sorted(excluded)} if excluded else {}),
                        "verbsDescription": vds,
                    },
                },
            }
            os.makedirs(rd_dir, exist_ok=True)
            os.makedirs(oas_dir, exist_ok=True)
            with open(os.path.join(oas_dir, f"{kind.lower()}.yaml"), "w") as fh:
                yaml.safe_dump(slice_spec, fh, sort_keys=False, width=120)
            header = (
                f"# GENERATED 1:1 from {os.path.basename(f)} — resource '{kind}'\n"
                f"# {'ASYNC (202+task): needs task-poll/ETag handling at runtime' if is_async else 'synchronous'}\n"
            )
            with open(os.path.join(rd_dir, f"{kind.lower()}.restdefinition.yaml"), "w") as fh:
                fh.write(header)
                yaml.safe_dump(rd, fh, sort_keys=False, width=120)
            sz = os.path.getsize(os.path.join(oas_dir, f"{kind.lower()}.yaml"))
            emitted.append((kind, "".join(a[0][0] for a in []) or "+".join(v[0] for v in verbs), "async" if is_async else "sync", sz))
            km_resources.append(f"  - {ns}/restdefinitions/{kind.lower()}.restdefinition.yaml")
            km_configmaps.append((cm_name, f"{ns}/oas/{kind.lower()}.yaml", kind.lower()))
            total_rd += 1

        if emitted:
            report.append(f"\n## {ns} ({len(emitted)} resources)\n")
            for kind, verbs, sync, sz in emitted:
                report.append(f"- **{kind}** — `{verbs}` — {sync} — slice {sz//1024}KB")

    # root kustomization for the generated set
    os.makedirs(OUT, exist_ok=True)
    km = ["apiVersion: kustomize.config.k8s.io/v1beta1", "kind: Kustomization",
          "namespace: nutanix-system", "",
          "resources:", "  - 00-namespace.yaml"] + sorted(set(km_resources)) + [
          "", "generatorOptions:", "  disableNameSuffixHash: true", "",
          "configMapGenerator:"]
    for cm_name, fpath, leaf in sorted(set(km_configmaps)):
        km += [f"  - name: {cm_name}", "    files:", f"      - {leaf}.yaml={fpath}"]
    with open(os.path.join(OUT, "kustomization.yaml"), "w") as fh:
        fh.write("\n".join(km) + "\n")
    with open(os.path.join(OUT, "00-namespace.yaml"), "w") as fh:
        fh.write("apiVersion: v1\nkind: Namespace\nmetadata:\n  name: nutanix-system\n")
    with open(os.path.join(OUT, "ANALYSIS.md"), "w") as fh:
        fh.write("\n".join(report) + f"\n\n**Total RestDefinitions generated: {total_rd}**\n")

    print(f"Generated {total_rd} RestDefinitions across namespaces into {OUT}/")
    # largest slice (must be <1MB for ConfigMap)
    biggest = 0
    for cm_name, fpath, leaf in km_configmaps:
        biggest = max(biggest, os.path.getsize(os.path.join(OUT, fpath)))
    print(f"Largest OAS slice: {biggest//1024} KB (ConfigMap limit ~1024 KB)")


if __name__ == "__main__":
    main()
