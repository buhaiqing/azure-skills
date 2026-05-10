# Azure CLI Conventions (Empirical Notes)

## Critical Behavioral Notes

### Output Format

**Rule**: Azure CLI outputs JSON by default (no flag needed). Use `--output table` for human-readable display only.

```bash
# CORRECT (default JSON)
az [service] [command]

# EXPLICIT JSON
az [service] [command] --output json

# HUMAN-READABLE (not for agent parsing)
az [service] [command] --output table
```

### Pagination Handling

Azure CLI automatically paginates. For large result sets:

```bash
# CLI handles pagination internally
az [service] [resource] list --resource-group "{{user.resource_group}}"

# For explicit control (rare)
az [service] [resource] list --resource-group "{{user.resource_group}}" --top 100
```

### Credential Sources (Priority Order)

| Priority | Source | Notes |
|----------|--------|-------|
| 1 | Environment vars | `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` |
| 2 | Azure CLI login | `az login` (interactive) |
| 3 | Managed Identity | Azure VM/Container App identity |

**Azure CLI reads credentials in this order automatically.**

### Location (Region) Handling

```bash
# Via environment
export AZURE_DEFAULT_LOCATION=eastus

# Via command flag
az [service] [command] --location westeurope

# List available locations
az account list-locations --output json
```

### Resource Group Handling

Resource Groups are Azure's container for resources (no AWS equivalent).

```bash
# Create resource group
az group create --name "{{user.resource_group}}" --location "{{user.location}}" --output json

# Show resource group
az group show --name "{{user.resource_group}}" --output json

# List resource groups
az group list --output json
```

### Resource ID Format

Azure uses full resource paths, not ARNs:

```
/subscriptions/{subscription-id}/resourceGroups/{rg-name}/providers/{provider}/{resource-type}/{resource-name}
```

Example:
```
/subscriptions/abc123-.../resourceGroups/my-rg/providers/Microsoft.Compute/virtualMachines/my-vm
```

### Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Missing `--resource-group` | All resource operations require resource group |
| Wrong location name | Use `az account list-locations` to verify |
| Resource not found | Check subscription ID and resource group |
| Asynchronous operation timeout | Poll for terminal state |

## Azure CLI vs AWS CLI Comparison

| Aspect | Azure CLI | AWS CLI |
|--------|-----------|---------|
| Default output | JSON | Needs `--output json` |
| Resource container | Resource Group | No equivalent |
| Region term | Location (`--location`) | Region (`--region`) |
| Auth method | `az login` or Service Principal | IAM credentials |
| Resource ID | Full path `/subscriptions/...` | ARN `arn:aws:...` |
| Async pattern | LRO (Long Running Operation) | Some services async |

## Retry Strategy

| Error Code | Retry? | Max Retries |
|------------|--------|-------------|
| 400 (InvalidParameter) | No | 0 |
| 403 (AccessDenied) | No | 0 |
| 404 (NotFound) | No | 0 |
| 409 (Conflict) | Yes | 1 |
| 429 (Throttling) | Yes | 3 with exponential backoff |
| 500 (InternalError) | Yes | 3 with exponential backoff |
| 503 (ServiceUnavailable) | Yes | 3 with exponential backoff |

## JSON Path Examples (Per Service)

Replace these examples with verified paths from actual Azure CLI runs:

```json
// Azure VM list
{
  "value": [
    {
      "id": "/subscriptions/.../resourceGroups/.../providers/Microsoft.Compute/virtualMachines/my-vm",
      "name": "my-vm",
      "location": "eastus",
      "properties": {
        "provisioningState": "Succeeded"
      }
    }
  ]
}
// JSON path: .value[0].name

// Azure Storage Account list
{
  "value": [
    {
      "name": "mystorageaccount",
      "location": "eastus",
      "kind": "StorageV2"
    }
  ]
}
// JSON path: .value[0].name
```

## Idempotency

Azure CLI commands are generally idempotent for:
- Get/List operations
- Delete operations (404 on second attempt)

For Create operations:
- Use unique names within resource group
- Azure supports `begin_create_or_update` (idempotent create/update)