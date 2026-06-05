#!/usr/bin/env python3
"""Serialized live-tester for PARENT-SCOPED read-observe RDs whose findby path has a
{clusterExtId} param. Supplies clusterExtId in the CR spec (path-param sourced from spec),
one controller at a time, longer poll to let the read-observe create-pending dance settle."""
import json, os, subprocess, time, yaml
REPO='/Users/diegobraga/krateo/nutanix'; CTX='kind-nova-kog'; NS='nutanix-system'
PROXY='http://nutanix-mw.nutanix-system.svc.cluster.local:8080'; SECRET='nutanix-pc-auth'
CLUSTER='00065368-b178-158a-2cb8-5254002ce452'
PC=os.environ.get('PC_BASE'); AUTH=os.environ.get('PC_AUTH')
def sh(*a,**k): return subprocess.run(a,capture_output=True,text=True,timeout=k.get('t',200),input=k.get('inp'))
def kc(*a,**k): return sh('kubectl','--context',CTX,*a,**k)
def auth_code(): return sh('curl','-sk','-u',AUTH,'-m','10','-o','/dev/null','-w','%{http_code}',PC+'/clustermgmt/v4.0/config/clusters?$limit=1',t=20).stdout.strip()
def crd_name(kind,group):
    return next((c['metadata']['name'] for c in json.loads(kc('get','crd','-o','json').stdout).get('items',[])
                 if c['spec']['names']['kind']==kind and c['spec']['group']==group), kind.lower()+'s.'+group)
RES=[('clustermgmt','host'),('clustermgmt','rackableunit'),('clustermgmt','physicalgpuprofile'),
     ('clustermgmt','virtualgpuprofile'),('clustermgmt','snmp'),('clustermgmt','datastore'),
     ('monitoring','tag'),('networking','remotesubnet'),('networking','remotevpnconnection'),
     ('networking','remotevtepgateway')]
results=[]
for ns,key in RES:
    if auth_code()!='200': print('!! auth locked -> abort'); break
    y=yaml.safe_load(open(f'{REPO}/generated/{ns}/restdefinitions/{key}.restdefinition.yaml'))
    r=y['spec']['resource']; kind=r['kind']; group=y['spec']['resourceGroup']
    cm=y['spec']['oasPath'].split('/')[3]; oaskey=y['spec']['oasPath'].split('/')[-1]
    sh('python3',f'{REPO}/scripts/patch_slice.py',f'{REPO}/generated/{ns}/oas/{key}.yaml',PROXY,'/tmp/_p.yaml')
    cmy=kc('create','configmap',cm,'-n',NS,'--from-file=%s=/tmp/_p.yaml'%oaskey,'--dry-run=client','-o','yaml').stdout
    kc('apply','-n',NS,'-f','-',inp=cmy)
    kc('apply','-f',f'{REPO}/generated/{ns}/restdefinitions/{key}.restdefinition.yaml')
    rd=kc('wait','-n',NS,'restdefinition/%s'%y['metadata']['name'],'--for=condition=Ready','--timeout=180s',t=200)
    cfg=("apiVersion: %s/v1alpha1\nkind: %sConfiguration\nmetadata: {name: nutanix-pc, namespace: %s}\nspec: {authentication: {basic: {usernameRef: {name: %s, namespace: %s, key: username}, passwordRef: {name: %s, namespace: %s, key: password}}}}\n"%(group,kind,NS,SECRET,NS,SECRET,NS))
    kc('apply','-f','-',inp=cfg)
    cr={'apiVersion':f'{group}/v1alpha1','kind':kind,'metadata':{'name':f'pt-{key}','namespace':NS},
        'spec':{'configurationRef':{'name':'nutanix-pc','namespace':NS},'clusterExtId':CLUSTER}}
    kc('apply','-f','-',inp=yaml.safe_dump(cr))
    crd=crd_name(kind,group); synced='?'; msg=''
    for _ in range(16):
        time.sleep(8)
        if auth_code()!='200': synced='LOCK'; break
        s=kc('get',crd,f'pt-{key}','-n',NS,'-o',"jsonpath={range .status.conditions[?(@.type=='Synced')]}{.status}|{.reason}|{.message}{end}").stdout.strip()
        if s: synced=s.split('|')[0]; msg='|'.join(s.split('|')[1:])
        if synced=='True': break
    print(f"{ns}/{key:28s} Synced={synced:6s} {msg[:70]}",flush=True)
    results.append((ns,key,synced,msg))
    kc('delete',crd,f'pt-{key}','-n',NS,'--ignore-not-found','--wait=false')
n=sum(1 for r in results if r[2]=='True')
print(f"\n=> PARENT-READ BATCH: {n}/{len(results)} Synced=True",flush=True)
for ns,key,s,m in results: print(f"  {ns}/{key}: {s} {m[:60]}")
