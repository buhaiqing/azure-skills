# Core Concepts Template (Azure Services)

Use this template when creating `references/core-concepts.md` for a new Azure service skill.

## Sections to Document

### 1. Service Overview

```markdown
## What is [Service Name]

- **Purpose**: Brief description of service capability
- **Category**: Compute / Storage / Database / Network / Security / Analytics / AI
- **Azure Portal URL**: https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/[provider]%2F[resourceType]
- **Official Docs**: https://docs.microsoft.com/azure/[service-area]/
- **Pricing**: https://azure.microsoft.com/pricing/details/[service]/
```

### 2. Primary Resources

```markdown
## Primary Resources

| Resource Type | Description | Portal Path |
|---------------|-------------|-------------|
| [Resource A] | Main resource | /providers/[provider]/[resourceA] |
| [Resource B] | Dependent resource | /providers/[provider]/[resourceB] |
```

### 3. Architecture & Limits

```markdown
## Architecture & Limits

### Location Availability
- Global service OR Regional service
- Supported locations: Use `az account list-locations` to verify

### Azure Resource ID Format
```
/subscriptions/{subscription-id}/resourceGroups/{rg}/providers/{provider}/{type}/{name}
```

### Quotas (Service Limits)
| Quota Name | Default Limit | Adjustable? |
|------------|---------------|-------------|
| Max [Resource] per [scope] | X | Yes (via support ticket) |
| Max concurrent operations | Y | No |

### Limits
- Max size: [specify]
- Max throughput: [specify]
- Rate limits: [specify]
```

### 4. Resource Lifecycle

```markdown
## Resource Lifecycle

| Provisioning State | Description | Allowed Operations |
|--------------------|-------------|-------------------|
| Creating | Initial provisioning | None (wait) |
| Succeeded | Operational | All operations |
| Updating | Configuration change | Limited |
| Deleting | Deletion in progress | None |
| Failed | Terminal error state | Delete or retry |

## Azure LRO (Long Running Operation)
- Azure uses `begin_*` methods for async operations
- Poller pattern: `poller.result()` waits for completion
- Terminal states: `Succeeded`, `Failed`, `Canceled`
```

### 5. Dependencies & Relationships

```markdown
## Dependencies

| Dependency | Required? | Created By |
|------------|-----------|------------|
| Resource Group | Yes | `azure-resource-ops` |
| Virtual Network | Optional | `azure-network-ops` |
| Storage Account | Optional | `azure-storage-ops` |
| Azure AD | Optional | `azure-rbac-ops` |

## Delegation Rules

1. Resource Group must exist before creating any resource → delegate to `azure-resource-ops`
2. Virtual Network required for VM → delegate to `azure-network-ops`
3. Storage Account required for some services → delegate to `azure-storage-ops`
```

### 6. Pricing Model (Brief)

```markdown
## Pricing Model (Summary)

- **Pricing type**: Consumption / Reserved / Spot
- **Key dimensions**: Instance type, storage size, data transfer, operations
- **Free tier**: Yes/No; [details - Azure Free Account]
- **Estimator**: https://azure.microsoft.com/pricing/calculator/
```

### 7. Best Practices

```markdown
## Best Practices

### Security
- Use Azure RBAC for access control
- Enable Azure Defender where applicable
- Encrypt data at rest and in transit
- Use Key Vault for secrets management

### Availability
- Multi-region deployment for critical services
- Use Availability Zones where supported
- Enable geo-replication for storage
- Implement backup and disaster recovery

### Cost
- Right-sizing recommendations
- Use Reserved Instances for stable workloads
- Monitor usage with Azure Cost Management
- Set spending limits and alerts
```

### 8. Common Patterns

```markdown
## Common Deployment Patterns

### Pattern 1: [Name]
- Use case: ...
- Architecture: ...
- CLI/SDK steps: ...

### Pattern 2: [Name]
- Use case: ...
- Architecture: ...
- CLI/SDK steps: ...
```

## Example (Azure Virtual Machines)

```markdown
## What is Azure Virtual Machines

- **Purpose**: Scalable compute capacity (virtual servers)
- **Category**: Compute
- **Portal**: https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.Compute%2FVirtualMachines
- **Docs**: https://docs.microsoft.com/azure/virtual-machines/
- **Pricing**: https://azure.microsoft.com/pricing/details/virtual-machines/

## Primary Resources

| Resource | Description | Portal Path |
|----------|-------------|-------------|
| Virtual Machine | Virtual server instance | /Microsoft.Compute/VirtualMachines |
| VM Image | OS template ( marketplace/custom) | /Microsoft.Compute/Images |
| Disk | Managed storage attached to VM | /Microsoft.Compute/Disks |

## Architecture & Limits

### Locations
- All Azure regions supported
- Region list: `az account list-locations`

### Resource ID
```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{vm-name}
```

### Quotas
| Quota | Default | Adjustable |
|-------|---------|------------|
| Max VMs per region | varies by type | Yes (support ticket) |
| Total regional vCPUs | varies | Yes (support ticket) |

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| Resource Group | Yes | `azure-resource-ops` |
| Virtual Network | Yes | `azure-network-ops` |
| Network Interface | Yes | `azure-network-ops` |
| Public IP | Optional | `azure-network-ops` |
| Storage (Disk) | Yes | `azure-storage-ops` |
```