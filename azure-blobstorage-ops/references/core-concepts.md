# Azure Blob Storage Core Concepts

## What is Azure Blob Storage

- **Purpose**: Object storage for unstructured data (files, images, videos, documents)
- **Category**: Storage / Object Storage
- **Portal**: https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.Storage%2FstorageAccounts
- **Docs**: https://docs.microsoft.com/azure/storage/blobs/
- **Pricing**: https://azure.microsoft.com/pricing/details/storage/blobs/

## Primary Resources

| Resource | Description | Portal Path |
|----------|-------------|-------------|
| Storage Account | Top-level storage container | /Microsoft.Storage/storageAccounts |
| Blob Container | Logical container for blobs | Containers in storage account |
| Blob | Individual file/object | Blobs in container |
| Blob Service | Storage account blob endpoint | Blob service properties |

## Architecture & Limits

### Resource ID Format
```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{account-name}
```

### Storage Account Limits

| Limit | Value | Adjustable |
|-------|-------|------------|
| Max storage account size | 5 PB | No (contact support for more) |
| Max containers per account | Unlimited | No |
| Max blobs per container | Unlimited | No |
| Max blob size | 190.7 TB (block blob) | No |
| Max block size | 100 MB (block blob) | No |
| Max request rate | 20,000 IOPS | Yes (support ticket) |

### Naming Constraints

| Resource | Rules |
|----------|-------|
| Storage Account | 3-24 chars, lowercase alphanumeric only |
| Container | 3-63 chars, lowercase alphanumeric, hyphens allowed |
| Blob | Up to 1024 chars, any valid URL chars |

### Endpoint URL Format

```
https://{account-name}.blob.core.windows.net/{container-name}/{blob-name}
```

## Storage Account Types

### General-purpose v2 (StorageV2)
- Recommended for most scenarios
- Supports all blob types
- Access tiers: Hot, Cool, Cold
- Lifecycle management
- Soft delete support

### General-purpose v1 (Storage)
- Legacy type
- Lower transaction costs for certain scenarios
- No access tiers
- Limited features

### BlobStorage
- Legacy blob-only type
- Access tiers supported
- No table/queue/file support
- Being deprecated

### Premium BlockBlobStorage
- High-performance SSD storage
- Premium tier only
- Lower latency, higher IOPS
- Use case: High-frequency access, real-time analytics

## Replication Options

### Locally-redundant Storage (LRS)
- 3 copies in single data center
- Lowest cost
- Protects against hardware failure
- Not protected against data center failure

### Zone-redundant Storage (ZRS)
- 3 copies across availability zones
- Medium cost
- Protected against zone failure
- Recommended for production within region

### Geo-redundant Storage (GRS)
- 6 copies across two regions (LRS in each)
- Higher cost
- Protected against region failure
- Use case: Disaster recovery

### Geo-zone-redundant Storage (GZRS)
- 6 copies across zones in two regions (ZRS + ZRS)
- Highest cost
- Maximum protection
- Use case: Mission-critical data

## Access Tiers

### Hot Tier
- Higher storage cost, lower access cost
- Optimized for frequent access
- Minimum storage period: None
- Use case: Active data, frequently accessed

### Cool Tier
- Lower storage cost, higher access cost
- Optimized for infrequent access
- Minimum storage period: 30 days
- Use case: Backup, infrequently accessed data

### Cold Tier
- Lowest storage cost, highest access cost
- Optimized for rarely accessed data
- Minimum storage period: 90 days
- Use case: Long-term backup, archive

### Archive Tier
- Lowest storage cost, highest access cost
- Data is offline, must be rehydrated
- Minimum storage period: 180 days
- Rehydration time: Up to 15 hours
- Use case: Long-term retention, compliance

## Blob Types

### Block Blob
- Composed of blocks (up to 100 MB each)
- Optimized for upload/download
- Max size: ~190.7 TB
- Use case: Documents, images, videos, logs

### Append Blob
- Append-only operations
- Optimized for logging
- Max size: 195 GB
- Use case: Logs, audit trails, telemetry

### Page Blob
- 512-byte page-aligned
- Optimized for random read/write
- Max size: 8 TB
- Use case: VHD files, Azure VM disks

## Security Features

### Access Control
| Method | Description |
|--------|-------------|
| **Azure AD** | Role-based access (recommended) |
| **Shared Key** | Account-level access key |
| **SAS Token** | Time-limited, scoped access |
| **Public Access** | Anonymous access (disable for security) |

### Data Protection
| Feature | Description |
|---------|-------------|
| **Soft Delete** | Recover deleted blobs (retention period) |
| **Versioning** | Maintain blob versions |
| **Immutable Storage** | WORM policy for compliance |
| **Encryption** | Server-side encryption (default) |
| **Customer-managed Keys** | Key Vault encryption keys |

## Lifecycle Management

### Rules-based Lifecycle
- Automatically move between tiers
- Automatically delete old blobs
- Based on age, access patterns
- Configurable policies per container/account

```json
{
  "rules": [
    {
      "name": "move-to-cool",
      "enabled": true,
      "type": "Lifecycle",
      "definition": {
        "filters": { "blobTypes": ["blockBlob"] },
        "actions": {
          "baseBlob": {
            "tierToCool": { "daysAfterModificationGreaterThan": 30 },
            "delete": { "daysAfterModificationGreaterThan": 365 }
          }
        }
      }
    }
  ]
}
```

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| Resource Group | Yes | `azure-resource-ops` |
| Virtual Network | No | `azure-network-ops` |
| Private Endpoint | No | `azure-network-ops` |
| Key Vault | No | `azure-keyvault-ops` |

## Best Practices

### Performance
- Use appropriate access tier
- Configure lifecycle policies
- Use premium tier for high-performance needs
- Parallel uploads for large blobs
- Use AzCopy for bulk operations

### Security
- Disable public blob access
- Use Azure AD authentication
- Enable soft delete
- Use customer-managed keys for sensitive data
- Apply lifecycle policies to clean up old data

### Cost Optimization
- Use Cool/Cold tier for infrequently accessed data
- Implement lifecycle policies
- Monitor storage usage
- Set retention policies
- Delete unused containers/blobs

## Pricing Model

- **Pricing type**: Storage cost + transaction cost + data transfer
- **Key dimensions**: Storage size, access tier, operations, data transfer, replication
- **Free tier**: Limited free storage in Azure Free Account
- **Estimator**: https://azure.microsoft.com/pricing/calculator/

## Common Patterns

### Pattern 1: Document Storage
- Use case: Application documents, user uploads
- Architecture: StorageV2 with Hot tier
- Steps:
  1. Create StorageV2 account
  2. Create containers per application
  3. Upload documents via SDK
  4. Implement access control

### Pattern 2: Backup Archive
- Use case: Long-term backup storage
- Architecture: StorageV2 with Cool/Cold tier + lifecycle
- Steps:
  1. Create StorageV2 account
  2. Set lifecycle policy (Hot → Cool → Archive)
  3. Upload backup files
  4. Configure retention period

### Pattern 3: Static Website
- Use case: Hosting static web content
- Architecture: StorageV2 with $web container
- Steps:
  1. Create StorageV2 account
  2. Enable static website feature
  3. Upload HTML/CSS/JS to $web container
  4. Configure custom domain

### Pattern 4: Data Lake (ADLS Gen2)
- Use case: Big data analytics
- Architecture: Hierarchical namespace enabled
- Steps:
  1. Create StorageV2 with hierarchical namespace
  2. Create file system (container)
  3. Organize data in directory structure
  4. Integrate with analytics services