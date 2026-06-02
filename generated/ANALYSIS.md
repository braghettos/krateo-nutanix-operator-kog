# Nutanix v4 API — resource inventory & generated RestDefinitions


## aiops (6 resources)

- **Scenario** — `findby+create+get+update+delete` — async — slice 94KB
- **Report** — `findby` — async — slice 20KB
- **Simulation** — `findby+create+get+update+delete` — async — slice 63KB
- **Source** — `findby` — async — slice 21KB
- **EntityDescriptor** — `findby` — async — slice 29KB
- **EntityType** — `findby` — async — slice 22KB

## clustermgmt (20 resources)

- **PcieDevice** — `findby` — async — slice 28KB
- **ClusterProfile** — `findby+create+get+update+delete` — async — slice 114KB
- **Cluster** — `findby+create+get+update+delete` — async — slice 135KB
- **Host** — `findby+get` — async — slice 53KB
- **BmcInfo** — `findby` — async — slice 40KB
- **HostNic** — `findby+get` — async — slice 47KB
- **VirtualNic** — `findby+get` — async — slice 43KB
- **PhysicalGpuProfile** — `findby` — async — slice 28KB
- **RackableUnit** — `findby+get` — async — slice 35KB
- **RsyslogServer** — `findby+create+get+update+delete` — async — slice 81KB
- **Snmp** — `findby` — async — slice 29KB
- **Trap** — `create+get+update+delete` — async — slice 67KB
- **User** — `create+get+update+delete` — async — slice 63KB
- **Datastore** — `findby` — async — slice 27KB
- **VirtualGpuProfile** — `findby` — async — slice 29KB
- **Disk** — `findby+get+delete` — async — slice 57KB
- **Host2** — `findby` — async — slice 41KB
- **StorageContainer** — `findby+create+get+update+delete` — async — slice 94KB
- **TaskResponse** — `get` — async — slice 37KB
- **VcenterExtension** — `findby+get` — async — slice 36KB

## datapolicies (1 resources)

- **ProtectionPolicy** — `findby+create+get+update+delete` — async — slice 93KB

## dataprotection (4 resources)

- **ProtectedResource** — `get` — async — slice 31KB
- **RecoveryPoint** — `findby+create+get+delete` — async — slice 77KB
- **VmRecoveryPoint** — `get` — async — slice 32KB
- **VssMetadata** — `findby` — async — slice 22KB

## files (22 resources)

- **FileServer** — `findby+get` — async — slice 35KB
- **AntiVirusServer** — `findby+create+get+update+delete` — async — slice 89KB
- **DnsRecord** — `findby` — async — slice 29KB
- **EmailConfig** — `findby` — async — slice 38KB
- **InfectedFile** — `findby+get+delete` — async — slice 54KB
- **MountTarget** — `findby+create+get+update+delete` — async — slice 119KB
- **QuotaPolicy** — `findby+create+get+update+delete` — async — slice 95KB
- **SnapshotChangedContent** — `findby+get` — async — slice 46KB
- **Snapshot** — `findby+create+get+delete` — async — slice 68KB
- **NotificationPolicy** — `findby+create+get+update+delete` — async — slice 98KB
- **ObjectStoreProfile** — `findby+create+get+update` — async — slice 81KB
- **PartnerServer** — `findby+create+get+update+delete` — async — slice 98KB
- **RansomwareConfig** — `findby+create+get+update+delete` — async — slice 82KB
- **Recommendation** — `findby+get+delete` — async — slice 42KB
- **VdiUserSession** — `findby+get+update` — async — slice 63KB
- **SnapshotSchedule** — `findby+create+get+update+delete` — async — slice 77KB
- **TierConfiguration** — `findby+create+get+update+delete` — async — slice 85KB
- **UserMapping** — `findby` — async — slice 20KB
- **VirusScanPolicy** — `findby+create+get+update+delete` — async — slice 85KB
- **ReplicationPolicy** — `findby+create+get+update+delete` — async — slice 102KB
- **UnifiedNamespace** — `findby+create+get+update+delete` — async — slice 80KB
- **ReplicationJob** — `findby+get` — async — slice 42KB

## iam (13 resources)

- **CertAuthProvider** — `findby+create+get+update+delete` — async — slice 66KB
- **DirectoryService** — `findby+create+get+update+delete` — async — slice 73KB
- **SamlIdentityProvider** — `findby+create+get+update+delete` — async — slice 72KB
- **SamlSpMetadata** — `findby` — async — slice 18KB
- **UserGroup** — `findby+create+get+delete` — async — slice 50KB
- **User** — `findby+create+get+update` — async — slice 71KB
- **BucketsAccessKey** — `findby+create+get+delete` — async — slice 54KB
- **Key** — `findby+create+get+delete` — async — slice 56KB
- **AuthorizationPolicy** — `findby+create+get+update+delete` — async — slice 72KB
- **Client** — `get` — async — slice 22KB
- **Entity** — `findby+get` — async — slice 38KB
- **Operation** — `findby+get` — async — slice 39KB
- **Role** — `findby+create+get+update+delete` — async — slice 66KB

## licensing (10 resources)

- **Eula** — `findby` — async — slice 23KB
- **Allowance** — `findby` — async — slice 30KB
- **Compliance** — `findby` — async — slice 35KB
- **Entitlement** — `findby` — async — slice 37KB
- **Feature** — `findby` — async — slice 34KB
- **LicenseKey** — `findby+create+get+delete` — async — slice 62KB
- **License** — `findby` — async — slice 37KB
- **Recommendation** — `findby` — async — slice 26KB
- **Setting** — `findby` — async — slice 28KB
- **Violation** — `findby` — async — slice 35KB

## lifecycle (8 resources)

- **Bundle** — `findby+create+get+delete` — async — slice 67KB
- **Config** — `findby` — async — slice 40KB
- **Entity** — `findby+get` — async — slice 44KB
- **Image** — `findby` — async — slice 30KB
- **LcmSummary** — `findby+get` — async — slice 38KB
- **Notification** — `get` — async — slice 28KB
- **Recommendation** — `get` — async — slice 28KB
- **Statu** — `findby` — async — slice 23KB

## microseg (6 resources)

- **AddressGroup** — `findby+create+get+update+delete` — async — slice 77KB
- **CategoryMapping** — `findby+create+get+update+delete` — async — slice 80KB
- **DirectoryServerConfig** — `findby+create+get+update+delete` — async — slice 80KB
- **Policy** — `findby+create+get+update+delete` — async — slice 101KB
- **Rule** — `findby` — async — slice 39KB
- **ServiceGroup** — `findby+create+get+update+delete` — async — slice 79KB

## monitoring (8 resources)

- **Alert** — `findby+get` — async — slice 52KB
- **EmailConfig** — `findby` — async — slice 55KB
- **SystemDefinedPolicy** — `findby+get` — async — slice 58KB
- **ClusterConfig** — `findby+get+update` — async — slice 69KB
- **UserDefinedPolicy** — `findby+create+get+update+delete` — async — slice 82KB
- **Audit** — `findby+get` — async — slice 46KB
- **Tag** — `findby` — async — slice 27KB
- **Event** — `findby+get` — async — slice 46KB

## multidomain (1 resources)

- **ExternalRepository** — `findby+create+get+update+delete` — async — slice 86KB

## networking (30 resources)

- **Capability** — `findby` — async — slice 22KB
- **Subnet** — `findby` — async — slice 27KB
- **Vpc** — `findby` — async — slice 22KB
- **BgpSession** — `findby+create+get+update+delete` — async — slice 163KB
- **BgpRoute** — `findby+get` — async — slice 44KB
- **Capability2** — `findby` — async — slice 28KB
- **RemoteSubnet** — `findby+get` — async — slice 63KB
- **RemoteVpnConnection** — `findby+get` — async — slice 51KB
- **RemoteVtepGateway** — `findby+get` — async — slice 40KB
- **Controller** — `findby+create+get+update+delete` — async — slice 77KB
- **FloatingIp** — `findby+create+get+update+delete` — async — slice 155KB
- **Gateway** — `findby+create+get+update+delete` — async — slice 126KB
- **IpfixExporter** — `findby+create+get+update+delete` — async — slice 81KB
- **Layer2Stretch** — `findby+create+get+update+delete` — async — slice 95KB
- **LearnedMacAddress** — `findby+get` — async — slice 42KB
- **LoadBalancerSession** — `findby+create+get+update+delete` — async — slice 97KB
- **NodeSchedulableStatuse** — `findby` — async — slice 26KB
- **RouteTable** — `findby+get` — async — slice 36KB
- **Route** — `findby+create+get+update+delete` — async — slice 90KB
- **RoutingPolicy** — `findby+create+get+update+delete` — async — slice 104KB
- **Subnet2** — `findby+create+get+update+delete` — async — slice 134KB
- **ReservedIp** — `findby` — async — slice 27KB
- **Vnic** — `findby` — async — slice 31KB
- **TrafficMirror** — `findby+create+get+update+delete` — async — slice 83KB
- **UplinkBond** — `findby+get` — async — slice 39KB
- **VirtualSwitch** — `findby+create+get+update+delete` — async — slice 91KB
- **VpcVirtualSwitchMapping** — `findby+create` — async — slice 42KB
- **Vpc2** — `findby+create+get+update+delete` — async — slice 90KB
- **VpnConnection** — `findby+create+get+update+delete` — async — slice 100KB
- **VpnVendorConfig** — `findby+get` — async — slice 37KB

## objects (3 resources)

- **ObjectStore** — `findby+create+get+update+delete` — async — slice 115KB
- **Certificate** — `findby+create+get` — async — slice 71KB
- **CertificateAuthority** — `findby` — async — slice 24KB

## opsmgmt (6 resources)

- **ReportConfig** — `findby+create+get+update+delete` — async — slice 109KB
- **Report** — `findby+create+get+delete` — async — slice 67KB
- **GlobalReportSetting** — `findby` — async — slice 50KB
- **ReportArtifact** — `findby+create` — async — slice 44KB
- **File** — `findby` — sync — slice 23KB
- **ContentFile** — `findby` — async — slice 25KB

## prism (8 resources)

- **Category** — `findby+create+get+update+delete` — async — slice 81KB
- **DomainManager** — `findby+create+get` — async — slice 74KB
- **Task** — `findby+get` — async — slice 43KB
- **BackupTarget** — `findby+create+get+update+delete` — async — slice 84KB
- **RestoreSource** — `create+get+delete` — sync — slice 41KB
- **RestorableDomainManager** — `findby` — sync — slice 45KB
- **RestorePoint** — `findby+get` — sync — slice 61KB
- **Batch** — `findby+get` — async — slice 37KB

## security (5 resources)

- **Credential** — `findby+create+get+update+delete` — async — slice 75KB
- **KeyManagementServer** — `findby+create+get+update+delete` — async — slice 74KB
- **ApprovalPolicy** — `findby+create+get+update` — async — slice 82KB
- **StigSummary** — `findby` — async — slice 27KB
- **Stig** — `findby` — async — slice 28KB

## storage (9 resources)

- **IscsiClient** — `findby+get` — async — slice 35KB
- **StorageContainer** — `findby+create+get+update+delete` — async — slice 62KB
- **Datastore** — `findby` — sync — slice 15KB
- **VolumeGroup** — `findby+create+get+delete` — async — slice 47KB
- **CategoryAssociation** — `findby` — sync — slice 14KB
- **Disk** — `findby+create+get+delete` — async — slice 48KB
- **IscsiClientAttachment** — `findby` — sync — slice 22KB
- **MetadataInfo** — `findby` — sync — slice 12KB
- **VmAttachment** — `findby` — sync — slice 13KB

## vmm (22 resources)

- **Vm** — `findby+create+get+update+delete` — async — slice 153KB
- **GuestTool** — `findby` — async — slice 37KB
- **CdRom** — `findby+create+get+delete` — async — slice 71KB
- **Disk** — `findby+create+get+update+delete` — async — slice 87KB
- **Gpu** — `findby+create+get+delete` — async — slice 68KB
- **Nic** — `findby+create+get+update+delete` — async — slice 91KB
- **PcieDevice** — `findby+create+get+delete` — async — slice 65KB
- **SerialPort** — `findby+create+get+update+delete` — async — slice 80KB
- **LegacyVmAntiAffinityPolicy** — `findby+delete` — async — slice 37KB
- **VmAntiAffinityPolicy** — `findby+create+get+update+delete` — async — slice 81KB
- **VmComplianceState** — `findby` — async — slice 31KB
- **VmHostAffinityPolicy** — `findby+create+get+update+delete` — async — slice 82KB
- **AhvVmComplianceState** — `findby` — async — slice 30KB
- **Image** — `findby+create+get+update+delete` — async — slice 84KB
- **File** — `findby` — async — slice 13KB
- **Template** — `findby+create+get+update+delete` — async — slice 189KB
- **Version** — `findby+get+delete` — async — slice 109KB
- **EsxiVm** — `findby+get` — async — slice 51KB
- **NutanixGuestTool** — `findby` — async — slice 37KB
- **EffectiveRateLimitPolicy** — `findby` — async — slice 27KB
- **PlacementPolicy** — `findby+create+get+update+delete` — async — slice 82KB
- **RateLimitPolicy** — `findby+create+get+update+delete` — async — slice 80KB

## volumes (7 resources)

- **IscsiClient** — `findby+get+update` — async — slice 59KB
- **VolumeGroup** — `findby+create+get+update+delete` — async — slice 93KB
- **CategoryAssociation** — `findby` — async — slice 26KB
- **Disk** — `findby+create+get+update+delete` — async — slice 86KB
- **ExternalIscsiAttachment** — `findby` — async — slice 26KB
- **Metadata** — `findby` — async — slice 21KB
- **VmAttachment** — `findby` — async — slice 24KB

**Total RestDefinitions generated: 189**
