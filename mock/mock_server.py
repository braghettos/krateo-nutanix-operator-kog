#!/usr/bin/env python3
"""
Mock Nutanix Prism Central v4 API - dependency-free (Python stdlib only).

Reproduces the behaviours that make the real v4 API awkward for oasgen, so the
generated RestDefinitions/controllers can be validated end-to-end WITHOUT a real
Prism Central:

  * {"data": ...} response envelope on GET/list
  * Category   -> synchronous full CRUD (POST/PUT return the entity)
  * VirtualMachine -> ASYNC: POST/PUT/DELETE return 202 + a TaskReference; the
    entity is materialised immediately and the task is reported SUCCEEDED
  * ETag on GET; If-Match required on PUT/DELETE (412 on mismatch)
  * Ntnx-Request-Id required on PUT/DELETE (400 if missing)
  * prism task endpoint so a poller can confirm completion

Auth is accepted permissively (Basic or X-Ntnx-Api-Key) - it only logs.

Run locally:   python3 mock_server.py            # http://127.0.0.1:8080
Env:           PORT (default 8080), HOST (default 0.0.0.0)
"""
import json
import os
import re
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# In-memory stores: kind -> { extId: {"entity": {...}, "etag": "N"} }
STORE = {"category": {}, "vm": {}, "image": {}, "subnet": {}, "cluster": {}}
TASKS = {}  # taskExtId -> {"extId":..., "status": "SUCCEEDED", "entityExtId":...}

# (method-agnostic) path patterns -> (kind, is_async)
COLLECTIONS = {
    r"^/api/prism/v4\.0/config/categories$": ("category", False),
    r"^/api/vmm/v4\.1/ahv/config/vms$": ("vm", True),
    r"^/api/vmm/v4\.1/content/images$": ("image", True),
    r"^/api/networking/v4\.0/config/subnets$": ("subnet", True),
    r"^/api/clustermgmt/v4\.0/config/clusters$": ("cluster", True),
}
ITEMS = {
    r"^/api/prism/v4\.0/config/categories/([^/]+)$": ("category", False),
    r"^/api/vmm/v4\.1/ahv/config/vms/([^/]+)$": ("vm", True),
    r"^/api/vmm/v4\.1/content/images/([^/]+)$": ("image", True),
    r"^/api/networking/v4\.0/config/subnets/([^/]+)$": ("subnet", True),
    r"^/api/clustermgmt/v4\.0/config/clusters/([^/]+)$": ("cluster", True),
}
TASK_RE = r"^/api/prism/v4\.0/config/tasks/([^/]+)$"


def match(table, path):
    for pat, meta in table.items():
        m = re.match(pat, path)
        if m:
            return meta, m
    return None, None


class Handler(BaseHTTPRequestHandler):
    # ---- helpers -------------------------------------------------------
    def _send(self, code, body=None, etag=None):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        if etag is not None:
            self.send_header("ETag", f'"{etag}"')
        self.end_headers()
        if body is not None:
            self.wfile.write(json.dumps(body).encode())

    def _read_body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return {}

    def _path(self):
        return self.path.split("?", 1)[0]

    def _query(self):
        if "?" not in self.path:
            return {}
        from urllib.parse import parse_qs
        return {k: v[0] for k, v in parse_qs(self.path.split("?", 1)[1]).items()}

    def _envelope(self, data):
        return {"data": data, "metadata": {"flags": []}}

    def _task_ref(self, kind, entity_ext_id):
        task_id = str(uuid.uuid4())
        TASKS[task_id] = {"extId": task_id, "status": "SUCCEEDED",
                          "entityExtId": entity_ext_id, "kind": kind}
        return task_id

    def log_message(self, fmt, *args):  # concise logging
        print("[mock] %s - %s" % (self.address_string(), fmt % args))

    # ---- verbs ---------------------------------------------------------
    def do_GET(self):
        path = self._path()

        # task polling
        meta, m = (None, re.match(TASK_RE, path))
        if m:
            t = TASKS.get(m.group(1))
            return self._send(200, self._envelope(t)) if t else self._send(404, {"error": "no such task"})

        # list (findby)
        meta, m = match(COLLECTIONS, path)
        if meta:
            kind = meta[0]
            q = self._query()
            items = [r["entity"] for r in STORE[kind].values()]
            f = q.get("$filter", "")
            for fld in ("name", "key", "value"):
                mm = re.search(fld + r"\s+eq\s+'([^']*)'", f)
                if mm:
                    items = [e for e in items if str(e.get(fld)) == mm.group(1)]
            return self._send(200, self._envelope(items))

        # get by id
        meta, m = match(ITEMS, path)
        if meta:
            kind = meta[0]
            rec = STORE[kind].get(m.group(1))
            if not rec:
                return self._send(404, {"error": "not found"})
            return self._send(200, self._envelope(rec["entity"]), etag=rec["etag"])

        return self._send(404, {"error": "unknown path", "path": path})

    def do_POST(self):
        path = self._path()
        meta, m = match(COLLECTIONS, path)
        if not meta:
            return self._send(404, {"error": "unknown path", "path": path})
        kind, is_async = meta
        body = self._read_body()
        ext_id = str(uuid.uuid4())
        entity = dict(body)
        entity["extId"] = ext_id
        STORE[kind][ext_id] = {"entity": entity, "etag": "0"}
        if is_async:
            task_id = self._task_ref(kind, ext_id)
            return self._send(202, self._envelope({"extId": task_id}))
        # synchronous (categories)
        return self._send(200, self._envelope(entity), etag="0")

    def _require_concurrency_headers(self, rec):
        """Return error tuple (code, body) or None if OK."""
        if not self.headers.get("Ntnx-Request-Id"):
            return (400, {"error": "Ntnx-Request-Id header required"})
        if_match = (self.headers.get("If-Match") or "").strip('"')
        if if_match != rec["etag"]:
            return (412, {"error": "ETag mismatch (If-Match required)",
                          "expected": rec["etag"], "got": if_match})
        return None

    def do_PUT(self):
        path = self._path()
        meta, m = match(ITEMS, path)
        if not meta:
            return self._send(404, {"error": "unknown path", "path": path})
        kind, is_async = meta
        rec = STORE[kind].get(m.group(1))
        if not rec:
            return self._send(404, {"error": "not found"})
        err = self._require_concurrency_headers(rec)
        if err:
            return self._send(*err)
        body = self._read_body()
        body["extId"] = m.group(1)
        rec["entity"] = body
        rec["etag"] = str(int(rec["etag"]) + 1)  # bump version
        if is_async:
            return self._send(202, self._envelope({"extId": self._task_ref(kind, m.group(1))}))
        return self._send(200, self._envelope(rec["entity"]), etag=rec["etag"])

    def do_DELETE(self):
        path = self._path()
        meta, m = match(ITEMS, path)
        if not meta:
            return self._send(404, {"error": "unknown path", "path": path})
        kind, is_async = meta
        rec = STORE[kind].get(m.group(1))
        if not rec:
            return self._send(404, {"error": "not found"})
        err = self._require_concurrency_headers(rec)
        if err:
            return self._send(*err)
        del STORE[kind][m.group(1)]
        if is_async:
            return self._send(202, self._envelope({"extId": self._task_ref(kind, m.group(1))}))
        return self._send(204)


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"[mock] Nutanix v4 mock listening on http://{host}:{port}/api")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
