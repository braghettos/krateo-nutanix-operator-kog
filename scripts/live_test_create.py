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

def role_operations():
    d=curl("/iam/v4.0/authz/operations?$limit=3").get('data') or []
    return [o['extId'] for o in d] or None

CAT=category_extid(); OPS=role_operations()
print('refs: cluster=%s  category=%s  ops=%d'%(CLUSTER[:12], (CAT or 'NONE')[:12], len(OPS or [])))
# vmm Filter has no discriminator -> the generated CRD rejects a nested $objectType; omit it.
FILT=lambda: {'type':'CATEGORIES_MATCH_ANY','categoryExtIds':[CAT]}

# (ns, key, body dict) — body fields only; proxy injects $objectType + NTNX-Request-Id (top level);
# nested objects need an explicit $objectType. clusterExtId is a path param sourced from spec.
RES=[
  # --- batch 1 (proven) ---
  ('aiops','simulation', {'name':'krateo-qs-ct-simulation','simulationSpec':{'hddGb':100,'ramGb':16,'vcpuCount':4}}),
  ('microseg','servicegroup', {'name':'krateo-qs-ct-servicegroup','description':'krateo live-test','tcpServices':[{'startPort':8080,'endPort':8080}]}),
  ('clustermgmt','storagecontainer', {'name':'krateo-qs-ct-storagecontainer'}),
  ('vmm','vmantiaffinitypolicy', {'name':'krateo-qs-ct-vmaap','categories':[{'extId':CAT}]} if CAT else None),
  # --- batch 2 ---
  ('iam','user', {'username':'krateo-qs-ct-svc','userType':'SERVICE_ACCOUNT','description':'krateo live-test svc acct'}),
  ('iam','role', {'displayName':'krateo-qs-ct-role','clientName':'krateo','operations':OPS} if OPS else None),
  ('clustermgmt','rsyslogserver', {'clusterExtId':CLUSTER,'serverName':'krateoqsctrsys','ipAddress':{'ipv4':{'value':'192.0.2.50'}},'port':514,'networkProtocol':'UDP'}),
  ('clustermgmt','trap', {'clusterExtId':CLUSTER,'address':{'ipv4':{'value':'192.0.2.60'}},'version':'V2','recieverName':'krateoqscttrap'}),
  ('vmm','placementpolicy', {'name':'krateo-qs-ct-pp','placementType':'SOFT','imageEntityFilter':FILT(),'clusterEntityFilter':FILT()} if CAT else None),
  ('vmm','ratelimitpolicy', {'name':'krateo-qs-ct-rlp','rateLimitKbps':1024,'clusterEntityFilter':FILT()} if CAT else None),
]

# Parent-chains: create a parent, capture its status.extId, thread it into each child's
# spec (the {…ExtId} path param is sourced from a spec field of the same name). volumes/disk
# needs no If-Match (only volumeGroupExtId) -> cleanest CREATE_NEEDS_PARENT proof.
_scs=curl("/clustermgmt/v4.0/config/storage-containers?$limit=10").get('data') or []
def _scid(c): return c.get('containerExtId') or c.get('extId')
SC=next((_scid(c) for c in _scs if c.get('name','').startswith('krateo-qs')), None) or next((_scid(c) for c in _scs),None)
CHAINS=[
  # vm -> serial-port: child POST needs the PARENT VM's If-Match (proxy injects it on 412/428).
  {'parent':('vmm','vm',{'name':'krateo-qs-ct-vmp','description':'krateo chain parent','numSockets':1,
                         'numCoresPerSocket':1,'memorySizeBytes':2147483648,'cluster':{'extId':CLUSTER}}),
   'find':('/vmm/v4.0/ahv/config/vms', 'name', 'krateo-qs-ct-vmp'),
   'children':[('vmm','serialport','vmExtId',{'index':0,'isConnected':False})]},
  # vg -> disk: chaining works (parent extId resolved + threaded), but this PC build's VolumeDisk
  # create requires a diskDataSourceReference (won't make a blank disk) -> VOL-40101. Left documented.
  {'parent':('volumes','volumegroup',{'name':'krateo-qs-ct-vgp','clusterReference':CLUSTER,'usageType':'USER'}),
   'find':('/volumes/v4.0/config/volume-groups', 'name', 'krateo-qs-ct-vgp'),
   'children':[('volumes','disk','volumeGroupExtId',{'index':0,'diskSizeBytes':1073741824,'storageContainerId':SC})]},
]
def find_extid(coll, field, val):
    import urllib.parse
    d=curl("%s?$filter=%s%%20eq%%20'%s'"%(coll, field, urllib.parse.quote(val))).get('data') or []
    return d[0].get('extId') if d else None

def provision(ns,key,body,crname):
    """patch slice -> RD -> Configuration -> CR; poll Synced; return (synced,msg,extId)."""
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
    cr={'apiVersion':f'{group}/v1alpha1','kind':kind,'metadata':{'name':crname,'namespace':NS},'spec':spec}
    kc('apply','-f','-',inp=yaml.safe_dump(cr))
    crd=crd_name(kind,group); synced='?'; msg=''; extId=None
    for _ in range(13):
        time.sleep(8)
        if auth_code()!='200': synced='LOCK'; break
        s=kc('get',crd,crname,'-n',NS,'-o',"jsonpath={range .status.conditions[?(@.type=='Synced')]}{.status}|{.reason}|{.message}{end}").stdout.strip()
        if s: synced=s.split('|')[0]; msg='|'.join(s.split('|')[1:])
        if synced=='True': break
    extId=kc('get',crd,crname,'-n',NS,'-o','jsonpath={.status.extId}').stdout.strip() or None
    return synced,msg,extId

ONLY=os.environ.get('ONLY')          # comma-list of keys to restrict the run (re-test subset)
DO_CHAINS=os.environ.get('CHAINS','')=='1'
if ONLY: RES=[r for r in RES if r[1] in ONLY.split(',')]
results=[]
if not DO_CHAINS:
  for ns,key,body in RES:
    if body is None: print(ns+'/'+key,'SKIP (no category ref)'); results.append((ns,key,'SKIP-noref','')); continue
    if auth_code()!='200': print('!! auth locked -> abort'); results.append((ns,key,'LOCK','')); break
    synced,msg,_=provision(ns,key,body,f'ct-{key}')
    print(f"{ns}/{key:28s} Synced={synced:6s} {msg[:80]}")
    results.append((ns,key,synced,msg))
else:
  for ch in CHAINS:
    pns,pkey,pbody=ch['parent']
    if auth_code()!='200': print('!! auth locked -> abort'); break
    psync,pmsg,pext=provision(pns,pkey,pbody,f'ct-{pkey}-parent')
    if not pext and 'find' in ch and psync=='True':
        pext=find_extid(*ch['find'])           # resolve parent extId from the PC by name
    print(f"[parent] {pns}/{pkey:20s} Synced={psync:6s} extId={str(pext)[:20]} {pmsg[:50]}")
    results.append((pns,pkey,psync,pmsg))
    if psync!='True' or not pext:
        print('   !! parent not ready/extId missing -> skipping children'); continue
    for cns,ckey,pfield,cbody in ch['children']:
        if auth_code()!='200': print('!! auth locked -> abort'); break
        b=dict(cbody); b[pfield]=pext
        csync,cmsg,_=provision(cns,ckey,b,f'ct-{ckey}-child')
        print(f"  [child] {cns}/{ckey:20s} Synced={csync:6s} ({pfield}={str(pext)[:12]}) {cmsg[:50]}")
        results.append((cns,ckey,csync,cmsg))

npass=sum(1 for r in results if r[2]=='True')
print(f"\n=> CREATE BATCH: {npass}/{sum(1 for r in results if r[2] not in ('SKIP-noref',))} created+Synced")
for ns,key,s,m in results: print(f"  {ns}/{key}: {s} {m[:70]}")
