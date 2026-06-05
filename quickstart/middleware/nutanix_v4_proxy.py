#!/usr/bin/env python3
"""
Nutanix v4 translating proxy for the Krateo KOG rest-dynamic-controller.

Sits between the controller and Prism Central and performs the runtime protocol
adaptations the Nutanix v4 API requires but a generic OpenAPI client does not do:

  1. OData $filter  : quote string values, and turn identifier params (?name=X,
                      ?extId=X) into `name eq 'X'` so findby works.
  2. $objectType    : inject the discriminator into create/update bodies, derived
                      generically from the request path (+ optional overrides).
  3. NTNX-Request-Id: inject a fresh UUID on POST/PUT/DELETE (idempotency).
  4. async tasks    : when the API returns 202 + a TaskReference, poll the task to
                      completion and return the real resource as a synchronous 200.
  5. ETag/If-Match  : on PUT/DELETE without If-Match, GET the resource first to
                      capture its ETag and add the header.
  5b. parent If-Match: on a child create (POST .../parent/{id}/children) that the API
                      rejects for a missing precondition (412/428), GET the parent and
                      retry with the parent's ETag — needed for VM disks/nics/serial-ports.

It is resource-agnostic: every translation is generic, so the same proxy serves
all Nutanix v4 RestDefinitions (vmm, clustermgmt, prism, networking, storage, ...).

Config (env):
  PC_BASE              required, e.g. https://pc.example.com:9440/api
  PORT                 default 8080
  TLS_VERIFY           "true"/"false" (default false; PC often uses a private CA)
  TASK_TIMEOUT_S       async task poll budget, seconds (default 180)
  OBJECTTYPE_OVERRIDES JSON map {"<path-prefix>": "<$objectType>"} for irregular cases
  LOG_LEVEL            INFO/DEBUG (default INFO)

Auth is NOT stored here: the controller's Authorization header is forwarded as-is
(and reused for the proxy's own task/ETag sub-requests).
"""
import http.server
import json
import os
import re
import ssl
import sys
import time
import uuid
import urllib.parse
import urllib.request
import urllib.error

PC_BASE = os.environ["PC_BASE"].rstrip("/")
PORT = int(os.environ.get("PORT", "8080"))
TLS_VERIFY = os.environ.get("TLS_VERIFY", "false").lower() == "true"
TASK_TIMEOUT_S = int(os.environ.get("TASK_TIMEOUT_S", "180"))
OVERRIDES = json.loads(os.environ.get("OBJECTTYPE_OVERRIDES", "{}"))
# Optional default cluster extId. Some v4 endpoints (e.g. networking/config/vpcs,
# clustermgmt storage-containers, the networking AWS subtree) require an
# `X-Cluster-Id` header to scope the request to a cluster. When set, the proxy
# adds it to every forwarded request that doesn't already carry one.
X_CLUSTER_ID = os.environ.get("X_CLUSTER_ID", "")
DEBUG = os.environ.get("LOG_LEVEL", "INFO").upper() == "DEBUG"

SSL_CTX = ssl.create_default_context() if TLS_VERIFY else ssl._create_unverified_context()


def log(level, msg):
    if level == "DEBUG" and not DEBUG:
        return
    sys.stdout.write("[%s] %s\n" % (level, msg))
    sys.stdout.flush()


# ---------------------------------------------------------------- $objectType ---
def _kind(collection):
    """`volume-groups` -> `VolumeGroup`, `categories` -> `Category`, `vms` -> `Vm`."""
    pascal = "".join(p[:1].upper() + p[1:] for p in collection.split("-"))
    if pascal.endswith("ies"):
        return pascal[:-3] + "y"
    if pascal.endswith("ss"):
        return pascal
    if pascal.endswith("s"):
        return pascal[:-1]
    return pascal


def _version(ver):
    """Path version -> $objectType version. GA `v4.0`->`v4`; alpha/beta `v4.0.a3`->`v4.r0.a3`."""
    parts = ver.split(".")
    if len(parts) <= 2:          # vX or vX.Y  (GA) -> drop the minor
        return parts[0]
    return ".".join([parts[0], "r" + parts[1]] + parts[2:])


def object_type_for(path):
    """Derive the Nutanix v4 $objectType discriminator from a request path."""
    p = path.split("?", 1)[0].strip("/")
    for prefix, ot in OVERRIDES.items():       # explicit overrides win
        if p == prefix.strip("/") or p.startswith(prefix.strip("/") + "/"):
            return ot
    segs = p.split("/")
    if len(segs) < 3:
        return None
    ns, ver, rest = segs[0], segs[1], segs[2:]
    if rest and rest[-1].startswith("{"):       # drop the resource's own {id}
        rest = rest[:-1]
    out, i = [], 0
    while i < len(rest):
        s = rest[i]
        if s.startswith("{"):                   # stray path param
            i += 1
            continue
        if i + 1 < len(rest) and rest[i + 1].startswith("{"):
            i += 2                              # parent collection + its id -> skip
            continue
        out.append(s)
        i += 1
    if not out:
        return None
    return ".".join([ns, _version(ver)] + out[:-1] + [_kind(out[-1])])


# ------------------------------------------------------------------- HTTP fwd ---
def forward(method, path, headers, body):
    req = urllib.request.Request(PC_BASE + path, data=body, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        r = urllib.request.urlopen(req, context=SSL_CTX, timeout=90)
        return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "nutanix-v4-proxy"

    def _auth(self):
        h = {"Accept": "application/json"}
        if self.headers.get("Authorization"):
            h["Authorization"] = self.headers["Authorization"]
        xcid = self.headers.get("X-Cluster-Id") or X_CLUSTER_ID
        if xcid:
            h["X-Cluster-Id"] = xcid
        return h

    def _read_body(self):
        if "chunked" in (self.headers.get("Transfer-Encoding") or "").lower():
            buf = []
            while True:
                line = self.rfile.readline().strip()
                try:
                    n = int(line.split(b";")[0], 16)
                except ValueError:
                    break
                if n == 0:
                    self.rfile.readline()
                    break
                buf.append(self.rfile.read(n))
                self.rfile.readline()
            return b"".join(buf)
        n = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(n) if n else b""

    # (1) findby filter shaping
    def _shape_query(self, path):
        if "?" not in path:
            return path
        base, q = path.split("?", 1)
        out, idents = [], []
        for k, v in urllib.parse.parse_qsl(q, keep_blank_values=True):
            if k == "$filter":
                out.append((k, re.sub(r"(\b[\w.]+\b)\s+eq\s+(?!')([^'\s)]+)", r"\1 eq '\2'", v)))
            elif k in ("name", "extId"):
                idents.append("%s eq '%s'" % (k, v))
            else:
                out.append((k, v))
        if idents:
            out.append(("$filter", " and ".join(idents)))
        return base + ("?" + urllib.parse.urlencode(out) if out else "")

    # (4) drive an async task to completion, return the resulting resource extId
    def _resolve_task(self, task_id, name, collection_path):
        tp = "/prism/v4.0/config/tasks/" + urllib.parse.quote(task_id, safe="")
        deadline = time.time() + TASK_TIMEOUT_S
        while time.time() < deadline:
            st, _, rb = forward("GET", tp, self._auth(), None)
            try:
                d = json.loads(rb).get("data", {})
            except ValueError:
                d = {}
            status = d.get("status")
            if status in ("SUCCEEDED", "FAILED", "CANCELED"):
                log("INFO", "task %s -> %s" % (task_id, status))
                if status != "SUCCEEDED":
                    return None
                if name:                                  # robust: re-find by name
                    fp = collection_path + "?$filter=" + urllib.parse.quote("name eq '%s'" % name)
                    _, _, frb = forward("GET", fp, self._auth(), None)
                    try:
                        data = json.loads(frb).get("data") or []
                        if data:
                            return data[0].get("extId")
                    except ValueError:
                        pass
                aff = [e.get("extId") for e in (d.get("entitiesAffected") or []) if e.get("extId")]
                # a child create affects both parent and child; the parent's extId is in the
                # collection path, so prefer the entity that is NOT the parent (the new child).
                for eid in aff:
                    if eid not in collection_path:
                        return eid
                return aff[0] if aff else None
            time.sleep(2)
        log("WARN", "task %s timed out" % task_id)
        return None

    def _proxy(self, method):
        path = self.path
        body = self._read_body()
        hdrs = self._auth()
        name = None

        if method == "GET":
            path = self._shape_query(path)

        if method in ("POST", "PUT"):
            if body:
                try:
                    obj = json.loads(body)
                    obj.pop("configurationRef", None)         # KOG-internal, not API
                    name = obj.get("name")
                    if "$objectType" not in obj:              # (2)
                        ot = object_type_for(path)
                        if ot:
                            obj["$objectType"] = ot
                    body = json.dumps(obj).encode()
                except ValueError:
                    log("WARN", "non-JSON %s body to %s" % (method, path))
            hdrs["Content-Type"] = "application/json"

        if method in ("POST", "PUT", "DELETE"):
            hdrs["NTNX-Request-Id"] = str(uuid.uuid4())       # (3)

        if method in ("PUT", "DELETE"):                       # (5)
            if self.headers.get("If-Match"):
                hdrs["If-Match"] = self.headers["If-Match"]
            else:
                _, gh, _ = forward("GET", path.split("?")[0], self._auth(), None)
                etag = gh.get("Etag") or gh.get("ETag")
                if etag:
                    hdrs["If-Match"] = etag

        st, rh, rb = forward(method, path, hdrs, body or None)
        log("DEBUG", "%s %s -> %s" % (method, path, st))

        # (5b) child-of-parent create: POST .../parent/{id}/children needs the PARENT's
        # If-Match (concurrency token on the parent, e.g. VM disks/nics/cd-roms). The
        # controller never sends one (patch_slice drops it as required), so only when the
        # API demands it (412/428) do we GET the parent resource and retry with its ETag.
        if method == "POST" and st in (409, 412, 428) and "If-Match" not in hdrs:
            parent = path.split("?")[0].rstrip("/").rsplit("/", 1)[0]
            _, ph, _ = forward("GET", parent, self._auth(), None)
            petag = ph.get("Etag") or ph.get("ETag")
            if petag:
                hdrs["If-Match"] = petag
                st, rh, rb = forward(method, path, hdrs, body or None)
                log("INFO", "retried POST %s with parent If-Match -> %s" % (path, st))

        if st == 202:                                         # (4) async resolution
            try:
                task = (json.loads(rb).get("data") or {}).get("extId")
            except ValueError:
                task = None
            coll = path.split("?")[0].rstrip("/")
            if method != "POST":
                coll = coll.rsplit("/", 1)[0]
            ext = self._resolve_task(task, name, coll) if task else None
            if method == "POST" and ext:
                st, rh, rb = forward("GET", coll + "/" + urllib.parse.quote(ext, safe=""), self._auth(), None)
            elif method == "DELETE":
                st, rb = 204, b""
            else:
                st, rb = 200, json.dumps({"data": {"extId": ext}}).encode()

        self.send_response(st)
        etag = rh.get("Etag") or rh.get("ETag")
        if etag:
            self.send_header("ETag", etag)
        self.send_header("Content-Type", rh.get("Content-Type", "application/json"))
        self.send_header("Content-Length", str(len(rb)))
        self.end_headers()
        if rb:
            self.wfile.write(rb)

    def do_GET(self):
        if self.path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        self._proxy("GET")

    def do_POST(self):
        self._proxy("POST")

    def do_PUT(self):
        self._proxy("PUT")

    def do_DELETE(self):
        self._proxy("DELETE")

    def log_message(self, *a):
        pass


def main():
    log("INFO", "nutanix-v4-proxy on :%d -> %s (tls_verify=%s)" % (PORT, PC_BASE, TLS_VERIFY))
    http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
