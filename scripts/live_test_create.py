#!/usr/bin/env python3
"""Serialized live-tester for CREATABLE Nutanix RDs through the KOG operator + proxy.
One controller at a time (lockout-safe): patch slice -> apply RD -> apply CR with a
fixture body -> wait Synced=True -> confirm on PC -> record. Leaves krateo-qs-ct-*
resources on the PC for inspection. Refs (cluster extId, a category extId) resolved up
front via the proxy-equivalent API reads."""
import json, os, subprocess, time, yaml

REPO='/Users/diegobraga/krateo/nutanix'; CTX='kind-nova-kog'; NS='nutanix-system'
PROXY='http://nutanix-mw.nutanix-system.svc.cluster.local:8080'
PC=os.environ.get('PC_BASE','https://<prism-central-host>:9440/api')
AUTH=os.environ.get('PC_AUTH','admin:<your-pc-password>'); SECRET='nutanix-pc-auth'
CLUSTER='00065368-b178-158a-2cb8-5254002ce452'

def sh(*a,**k): return subprocess.run(a,capture_output=True,text=True,timeout=k.get('t',120),input=k.get('inp'))
def kc(*a,**k): return sh('kubectl','--context',CTX,*a,**k)
def curl(path):
    r=sh('curl','-sk','-u',AUTH,'-m','15',PC+path,t=25);
    try: return json.loads(r.stdout)
    except Exception: return {}
def auth_code(): return sh('curl','-sk','-u',AUTH,'-m','10','-o','/dev/null','-w','%{http_code}',PC+'/clustermgmt/v4.0/config/clusters?$limit=1',t=20).stdout.strip()
def crd_name(kind,group):
    return next((c['metadata']['name'] for c in json.loads(kc('get','crd','-o','json').stdout).get('items',[])
                 if c['spec']['names']['kind']==kind and c['spec']['group']==group),'%s.%s'%(kind.lower()+'s',group))

# resolve a USER category extId for policy filters (create one via the controller path uses too much; read an existing one)
def category_extid():
    d=curl("/prism/v4.0/config/categories?$limit=50").get('data') or []
    return next((c['extId'] for c in d if c.get('type')=='USER'), d[0]['extId'] if d else None)

CAT=category_extid()
print('refs: cluster=%s  category=%s'%(CLUSTER[:12], (CAT or 'NONE')[:12]))

# (ns, key, body dict) — body fields only; proxy injects $objectType + NTNX-Request-Id (top level)
RES=[
  ('aiops','simulation', {'name':'krateo-qs-ct-simulation','simulationSpec':{'hddGb':100,'ramGb':16,'vcpuCount':4}}),
  ('microseg','servicegroup', {'name':'krateo-qs-ct-servicegroup','description':'krateo live-test','tcpServices':[{'startPort':8080,'endPort':8080}]}),
  ('clustermgmt','storagecontainer', {'name':'krateo-qs-ct-storagecontainer'}),
  ('vmm','vmantiaffinitypolicy', {'name':'krateo-qs-ct-vmaap','categories':[{'extId':CAT}]} if CAT else None),
  ('vmm','ratelimitpolicy', {'name':'krateo-qs-ct-rlp','rateLimitKbps':1024,'clusterEntityFilter':{'$objectType':'vmm.v4.images.config.Filter','type':'CATEGORIES_MATCH_ANY','categoryExtIds':[CAT]}} if CAT else None),
]

results=[]
for ns,key,body in RES:
    if body is None: print(ns+'/'+key,'SKIP (no category ref)'); results.append((ns,key,'SKIP-noref','')); continue
    if auth_code()!='200': print('!! auth locked -> abort'); results.append((ns,key,'LOCK','')); break
    y=yaml.safe_load(open(f'{REPO}/generated/{ns}/restdefinitions/{key}.restdefinition.yaml'))
    r=y['spec']['resource']; kind=r['kind']; group=y['spec']['resourceGroup']
    cm=y['spec']['oasPath'].split('/')[3]; oaskey=y['spec']['oasPath'].split('/')[-1]
    sh('python3',f'{REPO}/scripts/patch_slice.py',f'{REPO}/generated/{ns}/oas/{key}.yaml',PROXY,'/tmp/_cslice.yaml')
    cmy=kc('create','configmap',cm,'-n',NS,'--from-file=%s=/tmp/_cslice.yaml'%oaskey,'--dry-run=client','-o','yaml').stdout
    kc('apply','-n',NS,'-f','-',inp=cmy)
    kc('apply','-f',f'{REPO}/generated/{ns}/restdefinitions/{key}.restdefinition.yaml')
    kc('wait','-n',NS,'restdefinition/%s'%y['metadata']['name'],'--for=condition=Ready','--timeout=150s',t=170)
    cfg=("apiVersion: %s/v1alpha1\nkind: %sConfiguration\nmetadata: {name: nutanix-pc, namespace: %s}\nspec: {authentication: {basic: {usernameRef: {name: %s, namespace: %s, key: username}, passwordRef: {name: %s, namespace: %s, key: password}}}}\n"%(group,kind,NS,SECRET,NS,SECRET,NS))
    kc('apply','-f','-',inp=cfg)
    spec={'configurationRef':{'name':'nutanix-pc','namespace':NS}}; spec.update(body)
    cr={'apiVersion':f'{group}/v1alpha1','kind':kind,'metadata':{'name':f'ct-{key}','namespace':NS},'spec':spec}
    kc('apply','-f','-',inp=yaml.safe_dump(cr))
    crd=crd_name(kind,group); synced='?'; msg=''
    for _ in range(13):
        time.sleep(8)
        if auth_code()!='200': synced='LOCK'; break
        s=kc('get',crd,f'ct-{key}','-n',NS,'-o',"jsonpath={range .status.conditions[?(@.type=='Synced')]}{.status}|{.reason}|{.message}{end}").stdout.strip()
        if s: synced=s.split('|')[0]; msg='|'.join(s.split('|')[1:])
        if synced=='True': break
    print(f"{ns}/{key:28s} Synced={synced:6s} {msg[:80]}")
    results.append((ns,key,synced,msg))

npass=sum(1 for r in results if r[2]=='True')
print(f"\n=> CREATE BATCH: {npass}/{sum(1 for r in results if r[2] not in ('SKIP-noref',))} created+Synced")
for ns,key,s,m in results: print(f"  {ns}/{key}: {s} {m[:70]}")
