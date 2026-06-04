#!/usr/bin/env python3
"""Serialized live-tester for read-only Nutanix RestDefinitions through the KOG
operator + nutanix-v4 proxy. Processes RDs ONE AT A TIME (apply RD -> apply CR ->
wait Synced=True -> delete CR so the controller idles) to avoid storming the
shared PC admin account. Aborts immediately if auth ever locks (non-200).

Scope: read-observe RDs (no `create` verb) whose findby path has no parent path
param -> the CR is just {configurationRef}. Writes LIVE_TEST_RESULTS.md.
"""
import glob
import json
import os
import subprocess
import sys
import time

import yaml

REPO = '/Users/diegobraga/krateo/nutanix'
CTX = 'kind-nova-kog'
NS = 'nutanix-system'
PROXY = 'http://nutanix-mw.nutanix-system.svc.cluster.local:8080'
PC = 'https://141.94.131.53.nip.io:9441/api'
AUTH = 'admin:Krateo@Nutanix1'
SECRET = 'nutanix-pc-auth'

BLOCKED_NS = {'files', 'licensing', 'opsmgmt', 'objects', 'security', 'multidomain'}
BLOCKED_SPECIFIC = {
    ('aiops', 'source'), ('aiops', 'entitydescriptor'), ('aiops', 'entitytype'), ('aiops', 'report'),
    ('networking', 'capability'), ('networking', 'nodeschedulablestatuse'),
    ('prism', 'batch'), ('clustermgmt', 'bmcinfo'), ('clustermgmt', 'datastore'),
    ('storage', 'datastore'), ('dataprotection', 'vssmetadata'),
    ('prism', 'restorabledomainmanager'), ('prism', 'restorepoint'),
    ('vmm', 'effectiveratelimitpolicy'), ('microseg', 'rule'),
}


def sh(*args, timeout=120, inp=None):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, input=inp)


def kc(*args, **kw):
    return sh('kubectl', '--context', CTX, *args, **kw)


def auth_code():
    r = sh('curl', '-sk', '-u', AUTH, '-m', '10', '-o', '/dev/null', '-w', '%{http_code}',
           PC + '/clustermgmt/v4.0/config/clusters?$limit=1', timeout=20)
    return r.stdout.strip()


def discover():
    out = []
    for f in sorted(glob.glob(REPO + '/generated/*/restdefinitions/*.restdefinition.yaml')):
        try:
            y = yaml.safe_load(open(f))
            r = y['spec']['resource']
            verbs = {v['action']: v for v in r['verbsDescription']}
            if 'create' in verbs:
                continue
            fb = verbs.get('findby')
            if not fb or '{' in fb['path']:        # only top-level findby (no parent path param)
                continue
            ns = f.split('/generated/')[1].split('/')[0]
            key = os.path.basename(f).split('.')[0]
            if ns in BLOCKED_NS or (ns, key) in BLOCKED_SPECIFIC:
                continue
            out.append({
                'ns': ns, 'key': key, 'file': f,
                'rd': y['metadata']['name'], 'kind': r['kind'],
                'group': y['spec']['resourceGroup'],
                'oasfile': REPO + '/generated/%s/oas/%s.yaml' % (ns, key),
                'cm': y['spec']['oasPath'].split('/')[3],
                'oaskey': y['spec']['oasPath'].split('/')[-1],
            })
        except Exception as e:
            print('skip', f, e)
    return out


def run_one(rd):
    g, kind, group = rd, rd['kind'], rd['group']
    # 1. patch slice + configmap
    sh('python3', REPO + '/scripts/patch_slice.py', rd['oasfile'], PROXY, '/tmp/_slice.yaml')
    cmy = kc('create', 'configmap', rd['cm'], '-n', NS, '--from-file=%s=/tmp/_slice.yaml' % rd['oaskey'],
             '--dry-run=client', '-o', 'yaml').stdout
    kc('apply', '-n', NS, '-f', '-', inp=cmy)
    # 2. apply RD, wait Ready
    kc('apply', '-f', rd['file'])
    kc('wait', '-n', NS, 'restdefinition/%s' % rd['rd'], '--for=condition=Ready', '--timeout=150s', timeout=170)
    # 3. Configuration + read-only CR (spec = configurationRef only)
    cfg = ("apiVersion: %s/v1alpha1\nkind: %sConfiguration\nmetadata: {name: nutanix-pc, namespace: %s}\n"
           "spec: {authentication: {basic: {usernameRef: {name: %s, namespace: %s, key: username}, "
           "passwordRef: {name: %s, namespace: %s, key: password}}}}\n") % (group, kind, NS, SECRET, NS, SECRET, NS)
    cr = ("apiVersion: %s/v1alpha1\nkind: %s\nmetadata: {name: lt-%s, namespace: %s}\n"
          "spec: {configurationRef: {name: nutanix-pc, namespace: %s}}\n") % (group, kind, rd['key'], NS, NS)
    kc('apply', '-f', '-', inp=cfg)
    kc('apply', '-f', '-', inp=cr)
    # 4. poll Synced + auth
    plural = kind.lower() + 's'
    crd = '%s.%s' % (plural, group)
    synced, a = '?', '200'
    for _ in range(7):
        time.sleep(7)
        a = auth_code()
        if a != '200':
            break
        s = kc('get', crd, 'lt-%s' % rd['key'], '-n', NS,
               '-o', "jsonpath={range .status.conditions[?(@.type=='Synced')]}{.status}{end}").stdout.strip()
        synced = s or '?'
        if s == 'True':
            break
    # 5. delete the CR so the controller idles (read-only -> no external delete)
    kc('delete', crd, 'lt-%s' % rd['key'], '-n', NS, '--ignore-not-found', '--wait=false')
    return synced, a


def main():
    rds = discover()
    print('discovered %d read-observe RDs' % len(rds))
    results = []
    for i, rd in enumerate(rds, 1):
        if auth_code() != '200':
            print('!! auth locked before %s -> aborting' % rd['key'])
            results.append((rd, 'ABORTED-LOCK', 'lock'))
            break
        try:
            synced, a = run_one(rd)
        except Exception as e:
            synced, a = 'ERROR:%s' % str(e)[:60], auth_code()
        ok = 'PASS' if synced == 'True' else ('LOCK' if a != '200' else 'no-sync')
        print('[%d/%d] %-30s -> Synced=%s auth=%s %s' % (i, len(rds), rd['ns'] + '/' + rd['key'], synced, a, ok))
        results.append((rd, synced, a))
        if a != '200':
            print('!! auth dropped -> aborting'); break
    # write results
    npass = sum(1 for _, s, _ in results if s == 'True')
    lines = ['# Live-test results — read-observe batch (serialized via the operator)\n',
             '**%d / %d reached `Synced=True`** against the live PC (one controller at a time).\n' % (npass, len(results)),
             '| ns | kind | findby | Synced | auth |', '|---|---|---|---|---|']
    for rd, s, a in results:
        lines.append('| %s | %s | `%s` | %s | %s |' % (rd['ns'], rd['kind'], 'GET ' + rd['key'], s, a))
    open(REPO + '/LIVE_TEST_RESULTS.md', 'w').write('\n'.join(lines) + '\n')
    print('\n=> %d/%d PASS ; wrote LIVE_TEST_RESULTS.md' % (npass, len(results)))


if __name__ == '__main__':
    main()
