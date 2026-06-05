#!/usr/bin/env python3
"""Generalized parent-scoped read-observe sweep: each RD gets its parent path-param value
set in spec[field]. Parents resolved from the live PC. One controller at a time."""
import json, os, subprocess, time, yaml, ssl, base64, urllib.request, urllib.parse
REPO='/Users/diegobraga/krateo/nutanix'; CTX='kind-nova-kog'; NS='nutanix-system'
PROXY='http://nutanix-mw.nutanix-system.svc.cluster.local:8080'; SECRET='nutanix-pc-auth'
PC=os.environ['PC_BASE']; AUTH=os.environ['PC_AUTH']
ctx=ssl._create_unverified_context(); _h={'Authorization':'Basic '+base64.b64encode(AUTH.encode()).decode()}
def api(p):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(PC+p,headers=_h),timeout=12,context=ctx).read()).get('data') or []
    except Exception: return []
def first_ext(p):
    d=api(p); return d[0]['extId'] if d and isinstance(d[0],dict) and d[0].get('extId') else None
def sh(*a,**k): return subprocess.run(a,capture_output=True,text=True,timeout=k.get('t',200),input=k.get('inp'))
def kc(*a,**k): return sh('kubectl','--context',CTX,*a,**k)
def auth_code(): return sh('curl','-sk','-u',AUTH,'-m','10','-o','/dev/null','-w','%{http_code}',PC+'/clustermgmt/v4.0/config/clusters?$limit=1',t=20).stdout.strip()
def crd_name(kind,group):
    return next((c['metadata']['name'] for c in json.loads(kc('get','crd','-o','json').stdout).get('items',[])
                 if c['spec']['names']['kind']==kind and c['spec']['group']==group), kind.lower()+'s.'+group)
VG=first_ext("/volumes/v4.0/config/volume-groups?$limit=1")
TMPL=first_ext("/vmm/v4.0/content/templates?$limit=1")
SUB="9e7ad7e3-c53b-4e69-bd3c-15e552c6fb3e"
VAA=first_ext("/vmm/v4.0/ahv/policies/vm-anti-affinity-policies?$limit=1")
VHA=first_ext("/vmm/v4.0/ahv/policies/vm-host-affinity-policies?$limit=1")
VM=first_ext("/vmm/v4.0/ahv/config/vms?$filter="+urllib.parse.quote("name eq 'krateo-e2e-vm'"))
SDP=first_ext("/monitoring/v4.0/serviceability/alerts/system-defined-policies?$limit=1")
print('parents: VG=%s TMPL=%s VAA=%s VHA=%s VM=%s SDP=%s'%(str(VG)[:8],str(TMPL)[:8],str(VAA)[:8],str(VHA)[:8],str(VM)[:8],str(SDP)[:8]),flush=True)
RES=[('storage','categoryassociation','volumeGroupExtId',VG),('storage','iscsiclientattachment','volumeGroupExtId',VG),
     ('storage','metadatainfo','volumeGroupExtId',VG),('storage','vmattachment','volumeGroupExtId',VG),
     ('volumes','categoryassociation','volumeGroupExtId',VG),('volumes','externaliscsiattachment','volumeGroupExtId',VG),
     ('volumes','metadata','volumeGroupExtId',VG),('volumes','vmattachment','volumeGroupExtId',VG),
     ('vmm','version','templateExtId',TMPL),('networking','reservedip','subnetExtId',SUB),('networking','vnic','subnetExtId',SUB),
     ('vmm','vmcompliancestate','vmAntiAffinityPolicyExtId',VAA),('vmm','ahvvmcompliancestate','vmHostAffinityPolicyExtId',VHA),
     ('vmm','guesttool','extId',VM),('monitoring','clusterconfig','systemDefinedPolicyExtId',SDP)]
results=[]
for ns,key,field,pext in RES:
    if not pext: print(f"{ns}/{key:26s} SKIP (no parent extId)",flush=True); results.append((ns,key,'SKIP-noparent')); continue
    if auth_code()!='200': print('!! auth locked -> abort',flush=True); break
    y=yaml.safe_load(open(f'{REPO}/generated/{ns}/restdefinitions/{key}.restdefinition.yaml'))
    r=y['spec']['resource']; kind=r['kind']; group=y['spec']['resourceGroup']
    cm=y['spec']['oasPath'].split('/')[3]; oaskey=y['spec']['oasPath'].split('/')[-1]
    sh('python3',f'{REPO}/scripts/patch_slice.py',f'{REPO}/generated/{ns}/oas/{key}.yaml',PROXY,'/tmp/_p2.yaml')
    cmy=kc('create','configmap',cm,'-n',NS,'--from-file=%s=/tmp/_p2.yaml'%oaskey,'--dry-run=client','-o','yaml').stdout
    kc('apply','-n',NS,'-f','-',inp=cmy)
    kc('apply','-f',f'{REPO}/generated/{ns}/restdefinitions/{key}.restdefinition.yaml')
    kc('wait','-n',NS,'restdefinition/%s'%y['metadata']['name'],'--for=condition=Ready','--timeout=180s',t=200)
    cfg=("apiVersion: %s/v1alpha1\nkind: %sConfiguration\nmetadata: {name: nutanix-pc, namespace: %s}\nspec: {authentication: {basic: {usernameRef: {name: %s, namespace: %s, key: username}, passwordRef: {name: %s, namespace: %s, key: password}}}}\n"%(group,kind,NS,SECRET,NS,SECRET,NS))
    kc('apply','-f','-',inp=cfg)
    cr={'apiVersion':f'{group}/v1alpha1','kind':kind,'metadata':{'name':f'p2-{key}','namespace':NS},
        'spec':{'configurationRef':{'name':'nutanix-pc','namespace':NS},field:pext}}
    kc('apply','-f','-',inp=yaml.safe_dump(cr))
    crd=crd_name(kind,group); synced='?'; msg=''
    for _ in range(16):
        time.sleep(8)
        if auth_code()!='200': synced='LOCK'; break
        s=kc('get',crd,f'p2-{key}','-n',NS,'-o',"jsonpath={range .status.conditions[?(@.type=='Synced')]}{.status}|{.reason}|{.message}{end}").stdout.strip()
        if s: synced=s.split('|')[0]; msg='|'.join(s.split('|')[1:])
        if synced=='True': break
    print(f"{ns}/{key:26s} Synced={synced:6s} {msg[:70]}",flush=True)
    results.append((ns,key,synced))
    kc('delete',crd,f'p2-{key}','-n',NS,'--ignore-not-found','--wait=false')
n=sum(1 for r in results if r[2]=='True')
print(f"\n=> PARENT2 BATCH: {n}/{sum(1 for r in results if r[2] not in ('SKIP-noparent',))} Synced=True",flush=True)
for r in results: print('  %s/%s: %s'%r)
