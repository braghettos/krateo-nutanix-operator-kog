#!/usr/bin/env python3
"""Apply the 3 generic KOG/Nutanix-v4 slice-fixes to an OAS slice so the
rest-dynamic-controller can consume it through the nutanix-v4 proxy:

  1. servers[0].url -> the proxy service URL
  2. responses: expand range codes 4XX->400(/404), 5XX->500; add 200/201/202
     to post/put/patch/delete (the controller can't match range codes)
  3. parameters: drop required NTNX-Request-Id / If-Match (proxy injects them);
     add name + extId query params to the findby (list) GET op

Usage: patch_slice.py <in.yaml> <proxy-url> <out.yaml>
"""
import sys
import yaml


def patch(src_path, proxy_url):
    d = yaml.safe_load(open(src_path))
    d['servers'] = [{'url': proxy_url}]
    for path, methods in (d.get('paths') or {}).items():
        for m, op in methods.items():
            if not isinstance(op, dict):
                continue
            r = op.get('responses') or {}
            for old, new in (('4XX', '400'), ('5XX', '500')):
                if old in r:
                    r[new] = r.pop(old)
            if '400' in r and '404' not in r:
                r['404'] = r['400']
            if m in ('post', 'put', 'patch', 'delete'):
                base = r.get('202') or r.get('200') or {'description': 'OK'}
                for code in ('200', '201', '202'):
                    r.setdefault(code, base)
            op['responses'] = r
            ps = op.get('parameters')
            if ps:
                ps = [x for x in ps if str(x.get('name', '')).lower() not in ('ntnx-request-id', 'if-match', 'x-cluster-id')]
                op['parameters'] = ps
            # findby list op = GET on a collection path (no trailing {param})
            if m == 'get' and not path.rstrip('/').endswith('}'):
                ps = op.get('parameters') or []
                have = {x.get('name') for x in ps}
                for pn in ('name', 'extId'):
                    if pn not in have:
                        ps.append({'name': pn, 'in': 'query', 'required': False, 'schema': {'type': 'string'}})
                op['parameters'] = ps
    return d


if __name__ == '__main__':
    src, proxy, out = sys.argv[1], sys.argv[2], sys.argv[3]
    yaml.safe_dump(patch(src, proxy), open(out, 'w'), sort_keys=False)
    print('patched %s -> %s' % (src, out))
