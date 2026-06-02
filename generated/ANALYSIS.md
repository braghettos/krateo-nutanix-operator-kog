# Nutanix v4 API — resource inventory & generated RestDefinitions


## aiops (6 resources)

- **Scenario** — `findby+create+get+update+delete` — async — slice 98KB
- **Report** — `findby` — async — slice 21KB
- **Simulation** — `findby+create+get+update+delete` — async — slice 66KB
- **Source** — `findby` — async — slice 22KB
- **EntityDescriptor** — `findby` — async — slice 31KB
- **EntityType** — `findby` — async — slice 23KB

## clustermgmt (20 resources)

- **PcieDevice** — `findby` — async — slice 29KB
- **ClusterProfile** — `findby+create+get+update+delete` — async — slice 116KB
- **Cluster** — `findby+create+get+update+delete` — async — slice 137KB
- **Host** — `findby+get` — async — slice 55KB
- **BmcInfo** — `findby` — async — slice 41KB
- **HostNic** — `findby+get` — async — slice 49KB
- **VirtualNic** — `findby+get` — async — slice 44KB
- **PhysicalGpuProfile** — `findby` — async — slice 29KB
- **RackableUnit** — `findby+get` — async — slice 36KB
- **RsyslogServer** — `findby+create+get+update+delete` — async — slice 82KB
- **Snmp** — `findby` — async — slice 30KB
- **Trap** — `create+get+update+delete` — async — slice 68KB
- **User** — `create+get+update+delete` — async — slice 64KB
- **Datastore** — `findby` — async — slice 27KB
- **VirtualGpuProfile** — `findby` — async — slice 30KB
- **Disk** — `findby+get+delete` — async — slice 58KB
- **Host2** — `findby` — async — slice 43KB
- **StorageContainer** — `findby+create+get+update+delete` — async — slice 95KB
- **TaskResponse** — `get` — async — slice 38KB
- **VcenterExtension** — `findby+get` — async — slice 36KB

## datapolicies (1 resources)

- **ProtectionPolicy** — `findby+create+get+update+delete` — async — slice 94KB

## dataprotection (4 resources)

- **ProtectedResource** — `get` — async — slice 32KB
- **RecoveryPoint** — `findby+create+get+delete` — async — slice 79KB
- **VmRecoveryPoint** — `get` — async — slice 33KB
- **VssMetadata** — `findby` — async — slice 23KB

## files (22 resources)

- **FileServer** — `findby+get` — async — slice 36KB
- **AntiVirusServer** — `findby+create+get+update+delete` — async — slice 91KB
- **DnsRecord** — `findby` — async — slice 30KB
- **EmailConfig** — `findby` — async — slice 39KB
- **InfectedFile** — `findby+get+delete` — async — slice 54KB
- **MountTarget** — `findby+create+get+update+delete` — async — slice 121KB
- **QuotaPolicy** — `findby+create+get+update+delete` — async — slice 97KB
- **SnapshotChangedContent** — `findby+get` — async — slice 47KB
- **Snapshot** — `findby+create+get+delete` — async — slice 70KB
- **NotificationPolicy** — `findby+create+get+update+delete` — async — slice 99KB
- **ObjectStoreProfile** — `findby+create+get+update` — async — slice 82KB
- **PartnerServer** — `findby+create+get+update+delete` — async — slice 99KB
- **RansomwareConfig** — `findby+create+get+update+delete` — async — slice 83KB
- **Recommendation** — `findby+get+delete` — async — slice 43KB
- **VdiUserSession** — `findby+get+update` — async — slice 64KB
- **SnapshotSchedule** — `findby+create+get+update+delete` — async — slice 78KB
- **TierConfiguration** — `findby+create+get+update+delete` — async — slice 87KB
- **UserMapping** — `findby` — async — slice 20KB
- **VirusScanPolicy** — `findby+create+get+update+delete` — async — slice 86KB
- **ReplicationPolicy** — `findby+create+get+update+delete` — async — slice 103KB
- **UnifiedNamespace** — `findby+create+get+update+delete` — async — slice 81KB
- **ReplicationJob** — `findby+get` — async — slice 43KB

## iam (13 resources)

- **CertAuthProvider** — `findby+create+get+update+delete` — async — slice 67KB
- **DirectoryService** — `findby+create+get+update+delete` — async — slice 74KB
- **SamlIdentityProvider** — `findby+create+get+update+delete` — async — slice 73KB
- **SamlSpMetadata** — `findby` — async — slice 18KB
- **UserGroup** — `findby+create+get+delete` — async — slice 51KB
- **User** — `findby+create+get+update` — async — slice 73KB
- **BucketsAccessKey** — `findby+create+get+delete` — async — slice 55KB
- **Key** — `findby+create+get+delete` — async — slice 58KB
- **AuthorizationPolicy** — `findby+create+get+update+delete` — async — slice 72KB
- **Client** — `get` — async — slice 23KB
- **Entity** — `findby+get` — async — slice 39KB
- **Operation** — `findby+get` — async — slice 40KB
- **Role** — `findby+create+get+update+delete` — async — slice 67KB

## licensing (10 resources)

- **Eula** — `findby` — async — slice 23KB
- **Allowance** — `findby` — async — slice 30KB
- **Compliance** — `findby` — async — slice 36KB
- **Entitlement** — `findby` — async — slice 38KB
- **Feature** — `findby` — async — slice 34KB
- **LicenseKey** — `findby+create+get+delete` — async — slice 62KB
- **License** — `findby` — async — slice 37KB
- **Recommendation** — `findby` — async — slice 26KB
- **Setting** — `findby` — async — slice 29KB
- **Violation** — `findby` — async — slice 36KB

## lifecycle (8 resources)

- **Bundle** — `findby+create+get+delete` — async — slice 69KB
- **Config** — `findby` — async — slice 41KB
- **Entity** — `findby+get` — async — slice 45KB
- **Image** — `findby` — async — slice 31KB
- **LcmSummary** — `findby+get` — async — slice 39KB
- **Notification** — `get` — async — slice 29KB
- **Recommendation** — `get` — async — slice 29KB
- **Statu** — `findby` — async — slice 24KB

## microseg (6 resources)

- **AddressGroup** — `findby+create+get+update+delete` — async — slice 79KB
- **CategoryMapping** — `findby+create+get+update+delete` — async — slice 81KB
- **DirectoryServerConfig** — `findby+create+get+update+delete` — async — slice 81KB
- **Policy** — `findby+create+get+update+delete` — async — slice 104KB
- **Rule** — `findby` — async — slice 41KB
- **ServiceGroup** — `findby+create+get+update+delete` — async — slice 80KB

## monitoring (8 resources)

- **Alert** — `findby+get` — async — slice 55KB
- **EmailConfig** — `findby` — async — slice 56KB
- **SystemDefinedPolicy** — `findby+get` — async — slice 60KB
- **ClusterConfig** — `findby+get+update` — async — slice 70KB
- **UserDefinedPolicy** — `findby+create+get+update+delete` — async — slice 83KB
- **Audit** — `findby+get` — async — slice 47KB
- **Tag** — `findby` — async — slice 27KB
- **Event** — `findby+get` — async — slice 48KB

## multidomain (1 resources)

- **ExternalRepository** — `findby+create+get+update+delete` — async — slice 88KB

## networking (30 resources)

- **Capability** — `findby` — async — slice 23KB
- **Subnet** — `findby` — async — slice 28KB
- **Vpc** — `findby` — async — slice 23KB
- **BgpSession** — `findby+create+get+update+delete` — async — slice 166KB
- **BgpRoute** — `findby+get` — async — slice 45KB
- **Capability2** — `findby` — async — slice 29KB
- **RemoteSubnet** — `findby+get` — async — slice 65KB
- **RemoteVpnConnection** — `findby+get` — async — slice 52KB
- **RemoteVtepGateway** — `findby+get` — async — slice 41KB
- **Controller** — `findby+create+get+update+delete` — async — slice 78KB
- **FloatingIp** — `findby+create+get+update+delete` — async — slice 158KB
- **Gateway** — `findby+create+get+update+delete` — async — slice 129KB
- **IpfixExporter** — `findby+create+get+update+delete` — async — slice 82KB
- **Layer2Stretch** — `findby+create+get+update+delete` — async — slice 97KB
- **LearnedMacAddress** — `findby+get` — async — slice 43KB
- **LoadBalancerSession** — `findby+create+get+update+delete` — async — slice 99KB
- **NodeSchedulableStatuse** — `findby` — async — slice 27KB
- **RouteTable** — `findby+get` — async — slice 37KB
- **Route** — `findby+create+get+update+delete` — async — slice 92KB
- **RoutingPolicy** — `findby+create+get+update+delete` — async — slice 106KB
- **Subnet2** — `findby+create+get+update+delete` — async — slice 137KB
- **ReservedIp** — `findby` — async — slice 28KB
- **Vnic** — `findby` — async — slice 32KB
- **TrafficMirror** — `findby+create+get+update+delete` — async — slice 84KB
- **UplinkBond** — `findby+get` — async — slice 40KB
- **VirtualSwitch** — `findby+create+get+update+delete` — async — slice 93KB
- **VpcVirtualSwitchMapping** — `findby+create` — async — slice 43KB
- **Vpc2** — `findby+create+get+update+delete` — async — slice 92KB
- **VpnConnection** — `findby+create+get+update+delete` — async — slice 102KB
- **VpnVendorConfig** — `findby+get` — async — slice 46KB

## objects (3 resources)

- **ObjectStore** — `findby+create+get+update+delete` — async — slice 123KB
- **Certificate** — `findby+create+get` — async — slice 74KB
- **CertificateAuthority** — `findby` — async — slice 25KB

## opsmgmt (6 resources)

- **ReportConfig** — `findby+create+get+update+delete` — async — slice 114KB
- **Report** — `findby+create+get+delete` — async — slice 71KB
- **GlobalReportSetting** — `findby` — async — slice 51KB
- **ReportArtifact** — `findby+create` — async — slice 46KB
- **File** — `findby` — sync — slice 24KB
- **ContentFile** — `findby` — async — slice 26KB

## prism (8 resources)

- **Category** — `findby+create+get+update+delete` — async — slice 82KB
- **DomainManager** — `findby+create+get` — async — slice 75KB
- **Task** — `findby+get` — async — slice 44KB
- **BackupTarget** — `findby+create+get+update+delete` — async — slice 85KB
- **RestoreSource** — `create+get+delete` — sync — slice 42KB
- **RestorableDomainManager** — `findby` — sync — slice 46KB
- **RestorePoint** — `findby+get` — sync — slice 62KB
- **Batch** — `findby+get` — async — slice 38KB

## security (5 resources)

- **Credential** — `findby+create+get+update+delete` — async — slice 77KB
- **KeyManagementServer** — `findby+create+get+update+delete` — async — slice 76KB
- **ApprovalPolicy** — `findby+create+get+update` — async — slice 85KB
- **StigSummary** — `findby` — async — slice 29KB
- **Stig** — `findby` — async — slice 32KB

## storage (9 resources)

- **IscsiClient** — `findby+get` — async — slice 37KB
- **StorageContainer** — `findby+create+get+update+delete` — async — slice 65KB
- **Datastore** — `findby` — sync — slice 17KB
- **VolumeGroup** — `findby+create+get+delete` — async — slice 49KB
- **CategoryAssociation** — `findby` — sync — slice 15KB
- **Disk** — `findby+create+get+delete` — async — slice 50KB
- **IscsiClientAttachment** — `findby` — sync — slice 23KB
- **MetadataInfo** — `findby` — sync — slice 13KB
- **VmAttachment** — `findby` — sync — slice 14KB

## vmm (22 resources)

- **Vm** — `findby+create+get+update+delete` — async — slice 158KB
- **GuestTool** — `findby` — async — slice 38KB
- **CdRom** — `findby+create+get+delete` — async — slice 72KB
- **Disk** — `findby+create+get+update+delete` — async — slice 88KB
- **Gpu** — `findby+create+get+delete` — async — slice 69KB
- **Nic** — `findby+create+get+update+delete` — async — slice 92KB
- **PcieDevice** — `findby+create+get+delete` — async — slice 66KB
- **SerialPort** — `findby+create+get+update+delete` — async — slice 81KB
- **LegacyVmAntiAffinityPolicy** — `findby+delete` — async — slice 38KB
- **VmAntiAffinityPolicy** — `findby+create+get+update+delete` — async — slice 83KB
- **VmComplianceState** — `findby` — async — slice 32KB
- **VmHostAffinityPolicy** — `findby+create+get+update+delete` — async — slice 83KB
- **AhvVmComplianceState** — `findby` — async — slice 31KB
- **Image** — `findby+create+get+update+delete` — async — slice 85KB
- **File** — `findby` — async — slice 13KB
- **Template** — `findby+create+get+update+delete` — async — slice 195KB
- **Version** — `findby+get+delete` — async — slice 114KB
- **EsxiVm** — `findby+get` — async — slice 53KB
- **NutanixGuestTool** — `findby` — async — slice 38KB
- **EffectiveRateLimitPolicy** — `findby` — async — slice 27KB
- **PlacementPolicy** — `findby+create+get+update+delete` — async — slice 83KB
- **RateLimitPolicy** — `findby+create+get+update+delete` — async — slice 81KB

## volumes (7 resources)

- **IscsiClient** — `findby+get+update` — async — slice 60KB
- **VolumeGroup** — `findby+create+get+update+delete` — async — slice 94KB
- **CategoryAssociation** — `findby` — async — slice 26KB
- **Disk** — `findby+create+get+update+delete` — async — slice 87KB
- **ExternalIscsiAttachment** — `findby` — async — slice 27KB
- **Metadata** — `findby` — async — slice 21KB
- **VmAttachment** — `findby` — async — slice 25KB

**Total RestDefinitions generated: 189**
