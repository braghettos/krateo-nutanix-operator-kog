# Per-RestDefinition Live-Test Matrix — all 189 Nutanix v4 RDs

**Target:** live GA v4.0 Prism Central `pc.2024.3.1.13` at `https://<pc>:9441/api`, with the CE node registered as a PE (cluster `00065368-…`, AHV host present).
**Method:** Krateo KOG `rest-dynamic-controller` + the resource-agnostic `nutanix-v4-proxy` (injects `$objectType` from path, `NTNX-Request-Id`, resolves `202→task`, ETag/`If-Match`, quotes OData `$filter`). Every RD's OAS slice needs the 3 generic fixes (expand `4XX`/`5XX`→explicit + add `200/201/202`; drop required `NTNX-Request-Id`/`If-Match` params; add a `name`/`extId` findby param).

**Method legend**
- **READ_OBSERVE** — RD has no `create` verb. Apply RD + CR `{configurationRef}` only; controller runs findby/get → `Synced=True` (proven with monitoring/Alert).
- **CREATE_NOPARENT** — top-level `create`, body has no live-reference dependency.
- **CREATE_NEEDS_PARENT** — `requestFieldMapping` threads a parent's `status.extId` into a `{…ExtId}` path param; create the named parent first.
- **CREATE_NEEDS_REF** — top-level create but the body needs a live ref (PE cluster extId / seeded category / role-operation extIds / a VM extId).
- **BLOCKED** — with the precise GA_V4_FULL_CRUD.md cause.

Success bar = `Synced=True` AND (creatables) resource confirmed on PC. `status.extId`/`Ready` may lag for name-identified async creatables (known controller caveat) — noted, not a failure.

---

## Update 2026-06-11 — Small-PC rebuild: Atlas / Flow Virtual Networking now live

The totals below were captured on a STARTER / x-small PC with Atlas undeployed. The
target PC has since been rebuilt to **size Small** with **CMSP** + the **Network
Controller** enabled (PE registered). Re-probed 2026-06-11: **17 / 30 `networking`
RDs are route-reachable (200)** — up from 9 — and a `vpc2` create→delete plus a
5-RD Atlas sweep passed full-CRUD through the operator.

- **Now reachable (`N — Atlas` rows below are superseded):** `vpc2`, `subnet2`,
  `floatingip`, `gateway`, `routingpolicy`, `vpnconnection`, `bgpsession`,
  `layer2stretch`, `loadbalancersession`, `routetable`, `ipfixexporter`,
  `trafficmirror`, `virtualswitch`, `vpcvirtualswitchmapping`, `uplinkbond`,
  `controller`, `capability2`.
- **Still 400 — not Atlas:** parent-scoped children that need a parent `extId`
  (`bgproute`, `route`, `vnic`, `reservedip`, `learnedmacaddress`, `remotesubnet`,
  `remotevpnconnection`, `remotevtepgateway`, `vpnvendorconfig`); and the AWS cloud
  paths `/networking/v4.0/aws/*` (`capability`, `subnet`, `vpc`) + `nodeschedulablestatuse`
  (need AWS cloud connectivity).

---

## Totals on this environment

| | count |
|---|---:|
| **Live-testable (incl. read-only)** | **~98** |
| **Blocked** | **~91** |
| **Total** | **189** |

### By method (live-testable)
| Method | count | what |
|---|---:|---|
| READ_OBSERVE | ~55 | no create verb; CR is just `{configurationRef}` → findby/get → Synced=True |
| CREATE_NOPARENT | ~8 | category, addressgroup, servicegroup, userdefinedpolicy, protectionpolicy, simulation, placementpolicy, ratelimitpolicy (+ iam/user) |
| CREATE_NEEDS_PARENT | ~9 | bucketsaccesskey/key (parent user), storage&volumes disk (parent VG), vmm cdrom/disk/nic/serialport (parent vm), vmm version (parent template), monitoring clusterconfig |
| CREATE_NEEDS_REF | ~12 | rsyslogserver/trap/user/storagecontainer (cluster), role/authorizationpolicy, storage&volumes volumegroup, vm, recoverypoint (VM), vm{anti,host}affinitypolicy (categories), image (ISO), template (VM) |

### By namespace
| ns | testable | blocked | dominant blocker |
|---|---:|---:|---|
| aiops | 1 | 5 | Analytics service absent |
| clustermgmt | 18 | 2 | bmc/datastore HW |
| datapolicies | 1 | 0 | — |
| dataprotection | 2 | 2 | unimplemented/404 |
| files | 0 | 22 | Files service 503 |
| iam | 9 | 4 | external LDAP/IdP/cert |
| licensing | 0 | 10 | Licensing 503 |
| lifecycle | 7 | 1 | LCM artifact fixture |
| microseg | 2 | 4 | Flow EPM / directory |
| monitoring | 8 | 0 | — |
| multidomain | 0 | 1 | NS_ABSENT |
| networking | 9 | 21 | Atlas not configured |
| objects | 0 | 3 | Objects 503 |
| opsmgmt | 0 | 6 | Reporting 503 |
| prism | 3 | 5 | PE-only 501 / 503 |
| security | 0 | 5 | NS_ABSENT |
| storage | 8 | 1 | datastore sub-route |
| vmm | 20 | 2 | GPU HW / 500 backend |
| volumes | 7 | 0 | — |
| **Total** | **~98** | **~91** | |

---

## Recommended serialized execution order (one-controller-at-a-time)

The shared PC `admin` account locks (401) if many controllers storm it concurrently (recovery ~10–15 min of zero auth attempts). Run **one RD's controller at a time**: apply RD → `Synced=True` → apply CR → confirm → scale that controller to 0 → next. A single steady controller keeps auth 200.

- **Batch 0 — proxy + auth + refs (once):** deploy `nutanix-mw` (`PC_BASE`), create `nutanix-pc-auth` Secret + per-ns `*Configuration`. Capture the **PE cluster extId** and **operation extIds** (iam/operation) up front.
- **Batch 1 — READ_OBSERVE (~55, lowest risk):** read-only RDs serially; CR = `{configurationRef}` → Synced=True. Start with monitoring/alert (proven).
- **Batch 2 — CREATE_NOPARENT (~8):** category, addressgroup first, then servicegroup, userdefinedpolicy, protectionpolicy, simulation, placementpolicy, ratelimitpolicy, iam/user.
- **Batch 3 — CREATE_NEEDS_REF:** rsyslogserver/trap/user/storagecontainer (cluster extId); role → authorizationpolicy; storage/volumes volumegroup; vm (PE cluster); image (tiny ISO); seed categories → vm{anti,host}affinitypolicy.
- **Batch 4 — CREATE_NEEDS_PARENT + parent-dependent reads:** thread parent `status.extId` into child `spec.<parent>ExtId`. Chains: user→{bucketsaccesskey,key}; vm→{disk,nic,serialport,cdrom}+reads; template→version; VG→{disk}+VG-child reads; systemdefinedpolicy→clusterconfig; recoverypoint→vmrecoverypoint.

Never run two creating controllers at once; on any 401 burst, pause all controllers and wait out the cooldown.

---

## Per-RD matrix

> `method` = how to live-test · `dep` = fixture / parent / ref needed · `Y` testable here · `N` blocked (reason)

### aiops (6)
| kind | verbs | id | method | dep | here |
|---|---|---|---|---|---|
| entitydescriptor | findby | extId(sourceExtId) | READ_OBSERVE | source extId | N — needs source parent; Analytics absent |
| entitytype | findby | extId(sourceExtId) | READ_OBSERVE | source extId | N — Analytics absent |
| report | findby | extId(scenarioExtId) | READ_OBSERVE | scenario extId | N — Analytics absent |
| scenario | CRUD | name | CREATE_NOPARENT | capacity body | N — "Analytics service is not running" |
| simulation | CRUD | name | CREATE_NOPARENT | minimal sim body | **Y** — FULL_PASS, sync 201 |
| source | findby | extId | READ_OBSERVE | none | N — Analytics backend absent |

### clustermgmt (20)
| kind | verbs | id | method | dep | here |
|---|---|---|---|---|---|
| bmcinfo | findby | extId(clusterExtId) | READ_OBSERVE | cluster | N — 503 gRPC, no BMC on CE |
| cluster | CRUD | name | READ_OBSERVE (create disruptive) | — | **Y (read)** — list/get clusters 200 |
| clusterprofile | CRUD | name | CREATE_NOPARENT | — | N — 503 gRPC |
| datastore | findby | extId(clusterExtId) | READ_OBSERVE | cluster | N — needs ESXi PE |
| disk | findby,get,delete | extId | READ_OBSERVE | none | **Y** — READ_PASS |
| host | findby,get | extId(clusterExtId) | READ_OBSERVE | cluster | **Y** — READ_PASS |
| host2 | findby | extId | READ_OBSERVE | none | **Y** — READ_PASS |
| hostnic | findby,get | extId(clusterExtId) | READ_OBSERVE | cluster | **Y** — READ_PASS |
| pciedevice | findby | extId | READ_OBSERVE | none | **Y** — READ_PASS |
| physicalgpuprofile | findby | extId(clusterExtId) | READ_OBSERVE | cluster | **Y** — READ_PASS |
| rackableunit | findby,get | extId(clusterExtId) | READ_OBSERVE | cluster | **Y** — READ_PASS |
| rsyslogserver | CRUD | extId(clusterExtId) | CREATE_NEEDS_REF | PC cluster extId | **Y** — FULL_PASS, async |
| snmp | findby | extId(clusterExtId) | READ_OBSERVE | cluster | **Y** — READ_OBSERVE |
| storagecontainer | CRUD | name | CREATE_NEEDS_REF | PE cluster + X-Cluster-Id | **Y** — FULL_PASS |
| taskresponse | get | extId | READ_OBSERVE | a task extId | **Y (read)** |
| trap | create,get,update,delete | extId(clusterExtId) | CREATE_NEEDS_REF | cluster extId | **Y** — FULL_PASS, async |
| user | create,get,update,delete | extId(clusterExtId) | CREATE_NEEDS_REF | cluster extId | **Y** — FULL_PASS |
| vcenterextension | findby,get | extId | READ_OBSERVE | none | **Y (read)** — empty 200 |
| virtualgpuprofile | findby | extId(clusterExtId) | READ_OBSERVE | cluster | **Y** — READ_PASS |
| virtualnic | findby,get | extId(clusterExtId) | READ_OBSERVE | cluster | **Y** — READ_PASS |

### datapolicies (1)
| protectionpolicy | CRUD | name | CREATE_NOPARENT | local-only policy body | **Y** — FULL_PASS, async |

### dataprotection (4)
| kind | verbs | id | method | dep | here |
|---|---|---|---|---|---|
| protectedresource | get | extId | READ_OBSERVE | VM under protection policy | N — 404, needs protection policy |
| recoverypoint | findby,create,get,delete | name | CREATE_NEEDS_REF | a VM extId | **Y** — FULL_PASS once a VM exists |
| vmrecoverypoint | get | extId(recoveryPointExtId) | READ_OBSERVE | recoverypoint | **Y** — READ_PASS once an RP exists |
| vssmetadata | findby | extId(recoveryPointExtId) | READ_OBSERVE | recoverypoint | N — 501 Not Implemented |

### files (22) — entire namespace 503 (Files service not deployed)
All BLOCKED (Files backend `127.0.0.1:7509` down): antivirusserver, dnsrecord, emailconfig, fileserver, infectedfile, mounttarget, notificationpolicy, objectstoreprofile, partnerserver, quotapolicy, ransomwareconfig, recommendation, replicationjob, replicationpolicy, snapshot, snapshotchangedcontent, snapshotschedule, tierconfiguration, unifiednamespace, usermapping, vdiusersession, virusscanpolicy. (Method would be READ_OBSERVE for read-only ones / CREATE_NEEDS_PARENT under a `fileserver` for the rest, once Files is deployed.)

### iam (13)
| kind | verbs | id | method | dep | here |
|---|---|---|---|---|---|
| authorizationpolicy | CRUD | extId | CREATE_NEEDS_REF | a role extId | **Y** — FULL_PASS, sync |
| bucketsaccesskey | findby,create,get,delete | extId(userExtId) | CREATE_NEEDS_PARENT | user (svc-acct) | **Y** — FULL_PASS |
| certauthprovider | CRUD | name | CREATE_NEEDS_REF | DS + cert | N — external DS/cert |
| client | get | extId | READ_OBSERVE | none | **Y (read)** |
| directoryservice | CRUD | name | CREATE_NEEDS_REF | live LDAP | N — external LDAP |
| entity | findby,get | extId | READ_OBSERVE | none | **Y (read)** |
| key | findby,create,get,delete | name(userExtId) | CREATE_NEEDS_PARENT | user (svc-acct) | **Y** — FULL_PASS |
| operation | findby,get | extId | READ_OBSERVE | none | **Y (read)** — seeds role bodies |
| role | CRUD | extId | CREATE_NEEDS_REF | operation extIds | **Y** — FULL_PASS, sync |
| samlidentityprovider | CRUD | name | CREATE_NEEDS_REF | IdP metadata | N — external IdP |
| samlspmetadata | findby | extId | READ_OBSERVE | none | **Y (read)** |
| user | findby,create,get,update | extId | CREATE_NOPARENT | svc-acct body | **Y** — FULL_PASS (no delete verb) |
| usergroup | findby,create,get,delete | name | CREATE_NEEDS_REF | IdP/DS | N — needs IdP |

### licensing (10) — all 503 (CircuitBreaker open)
All BLOCKED: allowance, compliance, entitlement, eula, feature, license, licensekey, recommendation, setting, violation. (Read-only ones would be READ_OBSERVE; licensekey CREATE_NEEDS_REF (portal key) — once Licensing/entitlements available.)

### lifecycle (8)
| kind | verbs | id | method | dep | here |
|---|---|---|---|---|---|
| bundle | findby,create,get,delete | name | CREATE_NEEDS_REF | real LCM .tar.gz | N — artifact fixture |
| config | findby | extId | READ_OBSERVE | none | **Y (read)** |
| entity | findby,get | extId | READ_OBSERVE | none | **Y (read)** |
| image | findby | extId | READ_OBSERVE | none | **Y (read)** |
| lcmsummary | findby,get | extId | READ_OBSERVE | none | **Y (read)** |
| notification | get | extId | READ_OBSERVE | none | **Y (read)** |
| recommendation | get | extId | READ_OBSERVE | none | **Y (read)** |
| statu | findby | extId | READ_OBSERVE | none | **Y (read)** — generator-pluralized "Statu" |

### microseg (6)
| kind | verbs | id | method | dep | here |
|---|---|---|---|---|---|
| addressgroup | CRUD | name | CREATE_NOPARENT | `{name,ipv4Addresses[]}` | **Y** — FULL_PASS; worked example |
| categorymapping | CRUD | name | CREATE_NEEDS_REF | directory service | N — directory service |
| directoryserverconfig | CRUD | extId | CREATE_NEEDS_REF | directory service | N — directory service |
| policy | CRUD | name | CREATE_NOPARENT | Flow body | N — Flow not in EPM mode |
| rule | findby | extId(policyExtId) | READ_OBSERVE | policy | N — Flow EPM |
| servicegroup | CRUD | name | CREATE_NOPARENT | strip isSystemDefined | **Y** — FULL_PASS, async |

### monitoring (8)
| kind | verbs | id | method | dep | here |
|---|---|---|---|---|---|
| alert | findby,get | extId | READ_OBSERVE | none | **Y** — proven Synced=True |
| audit | findby,get | extId | READ_OBSERVE | none | **Y** — READ_PASS |
| clusterconfig | findby,get,update | extId(systemDefinedPolicyExtId) | CREATE_NEEDS_PARENT (update-only) | systemdefinedpolicy | **Y** — FULL_PASS |
| emailconfig | findby | extId | READ_OBSERVE | none | **Y (read)** |
| event | findby,get | extId | READ_OBSERVE | none | **Y** — READ_PASS |
| systemdefinedpolicy | findby,get | extId | READ_OBSERVE | none | **Y** — READ_PASS |
| tag | findby | extId(clusterExtId) | READ_OBSERVE | cluster | **Y (read)** |
| userdefinedpolicy | CRUD | extId | CREATE_NOPARENT | alert-policy body | **Y** — FULL_PASS, sync |

### multidomain (1)
| externalrepository | CRUD | name | CREATE_NOPARENT | — | N — NS_ABSENT (404) |

### networking (30)
| kind | verbs | id | method | dep | here |
|---|---|---|---|---|---|
| bgproute | findby,get | extId(bgpSessionExtId) | READ_OBSERVE | bgpsession | N — Atlas |
| bgpsession | CRUD | name | CREATE_NOPARENT | — | N — Atlas |
| capability | findby | extId | READ_OBSERVE | none | N — AWS subtree 500 |
| capability2 | findby | extId | READ_OBSERVE | none | **Y (read)** |
| controller | CRUD | extId | CREATE_NOPARENT | — | N — needs PC kSmall+ |
| floatingip | CRUD | name | CREATE_NOPARENT | — | N — Atlas |
| gateway | CRUD | name | CREATE_NOPARENT | — | N — Atlas |
| ipfixexporter | CRUD | name | CREATE_NOPARENT | — | N — Atlas |
| layer2stretch | CRUD | name | CREATE_NOPARENT | — | N — Atlas |
| learnedmacaddress | findby,get | extId(layer2StretchExtId) | READ_OBSERVE | layer2stretch | N — Atlas |
| loadbalancersession | CRUD | name | CREATE_NOPARENT | — | N — Atlas |
| nodeschedulablestatuse | findby | extId | READ_OBSERVE | X-Cluster-Id | N — 500 node-context |
| remotesubnet | findby,get | extId(clusterExtId) | READ_OBSERVE | cluster | **Y (read)** |
| remotevpnconnection | findby,get | extId(clusterExtId) | READ_OBSERVE | cluster | **Y (read)** |
| remotevtepgateway | findby,get | extId(clusterExtId) | READ_OBSERVE | cluster | **Y (read)** |
| reservedip | findby | extId(subnetExtId) | READ_OBSERVE | subnet | N — needs subnet (Atlas/VLAN) |
| route | CRUD | name(routeTableExtId) | CREATE_NEEDS_PARENT | routetable | N — Atlas |
| routetable | findby,get | extId | READ_OBSERVE | none | **Y (read)** |
| routingpolicy | CRUD | name | CREATE_NOPARENT | — | N — Atlas |
| subnet | findby | extId | READ_OBSERVE | none | **Y (read)** |
| subnet2 | CRUD | name | CREATE_NEEDS_REF | PE cluster + VLAN | N — VLAN/Atlas |
| trafficmirror | CRUD | name | CREATE_NOPARENT | — | N — Atlas |
| uplinkbond | findby,get | extId | READ_OBSERVE | none | **Y (read)** |
| virtualswitch | CRUD | name | CREATE_NOPARENT | — | N — Atlas/SDN write |
| vnic | findby | extId(subnetExtId) | READ_OBSERVE | subnet | N — needs subnet |
| vpc | findby | extId | READ_OBSERVE | none | **Y (read)** |
| vpc2 | CRUD | name | CREATE_NOPARENT | — | N — Atlas |
| vpcvirtualswitchmapping | findby,create | extId | CREATE_NOPARENT | — | N — Atlas |
| vpnconnection | CRUD | name | CREATE_NOPARENT | — | N — Atlas |
| vpnvendorconfig | findby,get | extId(vpnConnectionExtId) | READ_OBSERVE | vpnconnection | N — Atlas |

### objects (3) — 503 (Objects/MSP not deployed)
certificate (CREATE_NEEDS_PARENT objectstore), certificateauthority (READ_OBSERVE), objectstore (CREATE_NEEDS_REF CMSP+license) — all N.

### opsmgmt (6) — all 503 (Reporting service not running)
contentfile, file, globalreportsetting (READ_OBSERVE); report, reportartifact (CREATE_NEEDS_REF); reportconfig (CREATE_NOPARENT) — all N.

### prism (8)
| kind | verbs | id | method | dep | here |
|---|---|---|---|---|---|
| backuptarget | CRUD | extId(domainManagerExtId) | CREATE_NEEDS_PARENT | domainmanager | N — backup infra/PE-only |
| batch | findby,get | extId | READ_OBSERVE | none | N — 503 batch backend |
| category | CRUD | extId | CREATE_NOPARENT | `{key,value,type}` | **Y** — FULL_PASS; worked example |
| domainmanager | findby,create,get | extId | READ_OBSERVE (create=deploy PC) | none | **Y (read)** — PC self |
| restorabledomainmanager | findby | extId(restoreSourceExtId) | READ_OBSERVE | restoresource | N — 501 PE-only |
| restorepoint | findby,get | extId(restoreSourceExtId) | READ_OBSERVE | restoresource | N — 501 PE-only |
| restoresource | create,get,delete | extId | CREATE_NOPARENT | — | N — 501 PE-only |
| task | findby,get | extId | READ_OBSERVE | none | **Y (read)** |

### security (5) — NS_ABSENT (security/v4.0/* 404)
approvalpolicy, credential, keymanagementserver, stig, stigsummary — all N.

### storage (9) — alpha v4.0.a3
| kind | verbs | id | method | dep | here |
|---|---|---|---|---|---|
| categoryassociation | findby | extId(volumeGroupExtId) | READ_OBSERVE | VG | **Y** — READ_PASS once a VG exists |
| datastore | findby | extId | READ_OBSERVE | none | N — NS_ABSENT sub-route 404 |
| disk | findby,create,get,delete | extId(volumeGroupExtId) | CREATE_NEEDS_PARENT | VG | **Y** — FULL_PASS |
| iscsiclient | findby,get | extId | READ_OBSERVE | none | **Y (read)** |
| iscsiclientattachment | findby | extId(volumeGroupExtId) | READ_OBSERVE | VG | **Y** — READ_PASS |
| metadatainfo | findby | extId(volumeGroupExtId) | READ_OBSERVE | VG | **Y** — READ_PASS |
| storagecontainer | CRUD | name | READ_OBSERVE (create+list; by-id 404 → use clustermgmt) | — | **Y (read/create-list)** |
| vmattachment | findby | extId(volumeGroupExtId) | READ_OBSERVE | VG | **Y** — READ_PASS |
| volumegroup | findby,create,get,delete | name | CREATE_NEEDS_REF | `{name,clusterReference}` | **Y** — FULL_PASS (no longer 501); worked example |

### vmm (22)
| kind | verbs | id | method | dep | here |
|---|---|---|---|---|---|
| ahvvmcompliancestate | findby | extId(vmHostAffinityPolicyExtId) | READ_OBSERVE | host-affinity policy | **Y** — READ_PASS once policy exists |
| cdrom | findby,create,get,delete | extId(vmExtId) | CREATE_NEEDS_PARENT (parent-VM If-Match) | vm | **Y** — FULL_PASS |
| disk | CRUD | extId(vmExtId) | CREATE_NEEDS_PARENT | vm | **Y** — FULL_PASS |
| effectiveratelimitpolicy | findby | extId | READ_OBSERVE | none | N — 500 dependent backend |
| esxivm | findby,get | extId | READ_OBSERVE | none | **Y (read)** — empty 200 |
| file | findby | extId(imageExtId) | READ_OBSERVE | image | **Y** — READ_PASS once image exists |
| gpu | findby,create,get,delete | name(vmExtId) | CREATE_NEEDS_PARENT | vm | N (create, no GPU HW) / READ_PASS |
| guesttool | findby | extId | READ_OBSERVE | none | **Y** — READ_PASS |
| image | CRUD | name | CREATE_NEEDS_REF | tiny ISO URL | **Y** — FULL_PASS |
| legacyvmantiaffinitypolicy | findby,delete | extId | READ_OBSERVE | none | **Y (read)** |
| nic | CRUD | extId(vmExtId) | CREATE_NEEDS_PARENT (retain macAddress) | vm + subnet | **Y** — FULL_PASS |
| nutanixguesttool | findby | extId | READ_OBSERVE | none | **Y (read)** |
| pciedevice | findby,create,get,delete | extId(vmExtId) | CREATE_NEEDS_PARENT | vm | **Y** — READ_PASS |
| placementpolicy | CRUD | name | CREATE_NOPARENT | minimal body | **Y** — FULL_PASS, async |
| ratelimitpolicy | CRUD | extId | CREATE_NOPARENT | minimal body | **Y** — FULL_PASS, async |
| serialport | CRUD | extId(vmExtId) | CREATE_NEEDS_PARENT | vm | **Y** — FULL_PASS |
| template | CRUD | extId | CREATE_NEEDS_REF | source VM | **Y** — create from VM (no round-trip update) |
| version | findby,get,delete | extId(templateExtId) | CREATE_NEEDS_PARENT (create=new version) | template | **Y** — FULL_PASS once template exists |
| vm | CRUD | name | CREATE_NEEDS_REF | PE cluster (omit powerState) | **Y** — FULL_PASS; lead example |
| vmantiaffinitypolicy | CRUD | name | CREATE_NEEDS_REF | seeded category extIds | **Y** — FULL_PASS, async |
| vmcompliancestate | findby | extId(vmAntiAffinityPolicyExtId) | READ_OBSERVE | anti-affinity policy | **Y** — READ_PASS once policy exists |
| vmhostaffinitypolicy | CRUD | name | CREATE_NEEDS_REF | seeded category extIds | **Y** — FULL_PASS, async |

### volumes (7) — GA v4.0
| kind | verbs | id | method | dep | here |
|---|---|---|---|---|---|
| categoryassociation | findby | extId(volumeGroupExtId) | READ_OBSERVE | VG | **Y** — READ_PASS once a VG exists |
| disk | CRUD | extId(volumeGroupExtId) | CREATE_NEEDS_PARENT | VG | **Y** — VG child |
| externaliscsiattachment | findby | extId(volumeGroupExtId) | READ_OBSERVE | VG | **Y** — READ_PASS |
| iscsiclient | findby,get,update | extId | READ_OBSERVE | none | **Y (read)** |
| metadata | findby | extId(volumeGroupExtId) | READ_OBSERVE | VG | **Y** — READ_PASS |
| vmattachment | findby | extId(volumeGroupExtId) | READ_OBSERVE | VG | **Y** — READ_PASS |
| volumegroup | CRUD | name | CREATE_NEEDS_REF | `{name,clusterReference}` | **Y** — write path no longer 501 |

---

*Grounded in `GA_V4_FULL_CRUD.md` (per-RD verdicts) and each RD's verbs/identifiers/requestFieldMapping. Generated against live pc.2024.3.1.13.*
