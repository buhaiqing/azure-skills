# Azure File Storage Core Concepts

## What is Azure Files

- **Purpose**: Fully managed cloud file shares accessible via SMB (Server Message Block) and NFS (Network File System) protocols
- **Category**: Storage / Managed File Shares
- **Portal**: https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.Storage%2FstorageAccounts
- **Docs**: https://docs.microsoft.com/azure/storage/files/
- **Pricing**: https://azure.microsoft.com/pricing/details/storage/files/

## Primary Resources

| Resource | Description | Portal Path |
|----------|-------------|-------------|
| Storage Account | Top-level storage container (must be FileStorage or StorageV2) | /Microsoft.Storage/storageAccounts |
| File Share | Managed SMB/NFS file share | File shares in storage account |
| File Share Snapshot | Point-in-time read-only copy of a share | Snapshots under file share |
| File Service | Storage account file endpoint properties | File service properties |

## Resource ID Format

```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{account-name}/fileServices/default/shares/{share-name}
```

## Storage Account Types for Files

| Kind | Supports Files | Notes |
|------|----------------|-------|
| **StorageV2** | Yes (SMB only) | General-purpose v2, standard tier |
| **FileStorage** | Yes (SMB + NFS) | Premium tier, higher performance |
| **Storage** | Yes (SMB only) | Legacy v1, limited features |

## Protocols

### SMB (Server Message Block)
- Default protocol for Azure Files
- Supports Windows, Linux, and macOS clients
- Features: identity-based auth (AD DS, Azure AD DS), ACLs, persistent handles
- Port: 445 (must be open on client firewall)
- Access methods: Drive letter mapping, UNC path (`\\{account}.file.core.windows.net\{share}`)

### NFS (Network File System)
- Linux/Unix-native protocol (v4.1)
- Requires premium FileStorage account
- No AD/identity integration (IP-based access via network rules)
- Port: 2049
- No snapshot support via NFS protocol

## File Share Limits

| Limit | Standard (SMB) | Premium (SMB/NFS) |
|-------|----------------|--------------------|
| Max share size | 100 TiB | 100 TiB |
| Max file size | 1 TiB | 4 TiB |
| Max IOPS per share | 1,000 - 10,000 (burst) | 100,000 (provisioned) |
| Max throughput per share | Up to 60 MiB/s | Up to 6,204 MiB/s |
| Max open handles per file | 2,000 | 2,000 |
| Min quota | 1 GB | 100 GB |

## Naming Constraints

| Resource | Rules |
|----------|-------|
| Storage Account | 3-24 chars, lowercase alphanumeric only |
| File Share | 3-63 chars, lowercase letters, numbers, hyphens; no consecutive hyphens |
| File/Directory | Up to 255 chars per path component |

## Endpoint URL Format

```
https://{account}.file.core.windows.net/{share-name}/{path}
```

## Authentication Methods

| Method | Protocol | Description |
|--------|----------|-------------|
| **Storage Account Key** | SMB + NFS | Full access, root-level, use with `--account-key` |
| **Azure AD DS** | SMB only | Identity-based access via Azure AD Domain Services |
| **AD DS** | SMB only | On-premises Active Directory integration |
| **SAS Token** | SMB + NFS | Time-limited, scoped access |
| **Network rules** | NFS | IP-based access control (no identity) |

## Data Protection

### Soft Delete
- Recover accidentally deleted shares within retention period
- Enabled per storage account on file service properties
- Retention: 1-365 days
- Requires StorageV2 or FileStorage account

### Share Snapshots
- Point-in-time read-only copies
- Manual or scheduled via Azure Backup
- Can be used to restore individual files or entire share
- Billed on differential storage usage

### Backup
- Azure Backup supports Azure Files
- Scheduled snapshots with retention policies
- Restore to original or alternate location
- File-level recovery from restore point

## Redundancy Options (same as Storage Account)

| SKU | Replication | Use Case |
|-----|-------------|----------|
| Standard_LRS | Local redundant | Dev/test, non-critical |
| Standard_ZRS | Zone redundant | Production, HA within region |
| Standard_GRS | Geo redundant | Disaster recovery |
| Standard_GZRS | Geo + Zone redundant | Mission-critical |
| Premium_LRS | Premium local (FileStorage only) | High performance workloads |

## Performance Tiers

### Standard (SMB only)
- HDD-based, lower cost
- Pay-as-you-go (provisioned quota)
- Burstable IOPS
- Max 100 TiB per share

### Premium (SMB + NFS)
- SSD-based, higher cost
- Provisioned IOPS and throughput (based on quota)
- Consistent low latency (sub-ms for SMB)
- Requires FileStorage account

## Sync Options

### Azure File Sync
- Cache Azure file shares on on-premises Windows Servers
- Multi-site sync, cloud tiering
- Requirements: Windows Server 2012+, File Sync agent
- Use cases: Branch office consolidation, hybrid migration

## RBAC Roles for File Storage

| Role | Permissions |
|------|-------------|
| **Storage File Data SMB Share Reader** | Read SMB file shares (AD auth) |
| **Storage File Data SMB Share Contributor** | Read, write, delete SMB shares |
| **Storage File Data SMB Share Elevated Contributor** | Full SMB access including ACL changes |
| **Storage Account Contributor** | Manage storage accounts (create/delete shares via management plane) |

## Common Patterns

### Pattern 1: Application Shared Storage
- Use case: Multiple VMs sharing files
- Architecture: StorageV2 account with SMB share
- Steps: Create account → create SMB share → mount on VMs via UNC path

### Pattern 2: Linux NFS Workload
- Use case: Linux-based shared file system
- Architecture: FileStorage account with NFS share
- Steps: Create FileStorage account → create NFS share → mount via NFS v4.1

### Pattern 3: Hybrid File Server
- Use case: On-premises file server migration
- Architecture: Azure File Sync with cloud tiering
- Steps: Deploy File Sync agent → register server → create sync group

### Pattern 4: Backup and Disaster Recovery
- Use case: File share backups with snapshots
- Architecture: Azure Backup + share snapshots
- Steps: Configure backup vault → set backup policy → monitor restore points
