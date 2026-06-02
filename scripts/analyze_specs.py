#!/usr/bin/env python3
"""Analyze the official Nutanix v4 OpenAPI specs in oas/_official/.

Groups operations into "resources" (by the collection path) and reports CRUD
coverage + async (202/TaskReference) usage — the inputs needed to generate
1:1 Krateo RestDefinitions.
"""
import glob
import os
import re
import sys
from collections import defaultdict

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")

SPEC_DIR = os.path.join(os.path.dirname(__file__), "..", "oas", "_official")


def resource_key(path):
    """Collapse a path to its resource collection, e.g.
    /vmm/v4.0/ahv/config/vms/{extId}/nics/{nicExtId} -> .../vms/{}/nics"""
    # strip trailing /{param}
    p = re.sub(r"/\{[^/}]+\}$", "", path)
    return p


def main():
    grand_ops = 0
    rows = []
    for f in sorted(glob.glob(os.path.join(SPEC_DIR, "*.yaml"))):
        ns = os.path.basename(f).rsplit("-", 1)[0]
        spec = yaml.safe_load(open(f))
        paths = spec.get("paths", {})
        resources = defaultdict(lambda: {"verbs": set(), "async": False, "id_path": False})
        ops = 0
        for path, item in paths.items():
            rk = resource_key(path)
            has_id = bool(re.search(r"/\{[^/}]+\}$", path))
            for method, op in item.items():
                if method.lower() not in ("get", "post", "put", "patch", "delete"):
                    continue
                ops += 1
                grand_ops += 1
                r = resources[rk]
                r["verbs"].add(method.upper())
                if has_id:
                    r["id_path"] = True
                # async detection: 202 response or TaskReference in responses
                resp = op.get("responses", {})
                blob = str(resp)
                if "202" in resp or "TaskReference" in blob:
                    r["async"] = True
        rows.append((ns, len(paths), ops, resources))

    print(f"{'NAMESPACE':16}{'PATHS':>7}{'OPS':>6}{'RESOURCES':>11}  ASYNC?")
    print("-" * 70)
    detail = []
    for ns, npaths, ops, resources in rows:
        n_async = sum(1 for r in resources.values() if r["async"])
        print(f"{ns:16}{npaths:>7}{ops:>6}{len(resources):>11}  {n_async}/{len(resources)} async")
        for rk, r in sorted(resources.items()):
            verbs = "".join(sorted(r["verbs"]))
            # CRUD-able = has POST(create) and an id path (get/put/delete by id)
            crud = ("POST" in r["verbs"]) and r["id_path"]
            detail.append((ns, rk, "".join(sorted(r["verbs"])), "async" if r["async"] else "sync", "CRUD" if crud else ""))
    print(f"\nTOTAL operations: {grand_ops}\n")
    print("=== RESOURCE DETAIL (namespace | resource | verbs | sync | crud) ===")
    for ns, rk, verbs, sync, crud in detail:
        print(f"{ns:13} {rk:60} {verbs:18} {sync:6} {crud}")


if __name__ == "__main__":
    main()
