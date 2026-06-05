# Live-test results — read-observe batch (serialized via the operator)

**22 / 27 reached `Synced=True`** against the live PC (one controller at a time).

| ns | kind | findby | Synced | auth |
|---|---|---|---|---|
| clustermgmt | Disk | `GET disk` | True | 200 |
| clustermgmt | Host2 | `GET host2` | True | 200 |
| clustermgmt | PcieDevice | `GET pciedevice` | True | 200 |
| clustermgmt | VcenterExtension | `GET vcenterextension` | True | 200 |
| iam | Entity | `GET entity` | True | 200 |
| iam | Operation | `GET operation` | True | 200 |
| iam | SamlSpMetadata | `GET samlspmetadata` | False | 200 |
| lifecycle | Config | `GET config` | True | 200 |
| lifecycle | Entity | `GET entity` | True | 200 |
| lifecycle | Image | `GET image` | False | 200 |
| lifecycle | LcmSummary | `GET lcmsummary` | True | 200 |
| lifecycle | Statu | `GET statu` | ? | 200 |
| monitoring | Alert | `GET alert` | True | 200 |
| monitoring | Audit | `GET audit` | True | 200 |
| monitoring | EmailConfig | `GET emailconfig` | True | 200 |
| monitoring | Event | `GET event` | True | 200 |
| monitoring | SystemDefinedPolicy | `GET systemdefinedpolicy` | True | 200 |
| networking | Capability2 | `GET capability2` | True | 200 |
| networking | RouteTable | `GET routetable` | True | 200 |
| networking | Subnet | `GET subnet` | False | 200 |
| networking | UplinkBond | `GET uplinkbond` | True | 200 |
| networking | Vpc | `GET vpc` | False | 200 |
| prism | Task | `GET task` | True | 200 |
| storage | IscsiClient | `GET iscsiclient` | True | 200 |
| vmm | EsxiVm | `GET esxivm` | True | 200 |
| vmm | LegacyVmAntiAffinityPolicy | `GET legacyvmantiaffinitypolicy` | True | 200 |
| volumes | IscsiClient | `GET iscsiclient` | True | 200 |
