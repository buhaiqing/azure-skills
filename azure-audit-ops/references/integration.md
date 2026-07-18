# Integration Setup — azure-audit-ops

## Required Permissions

| Role | Minimum Scope | Required For |
|------|--------------|--------------|
| **Reader** | Subscription | Read Activity Log, RBAC, Locks, Resources |
| **Security Reader** | Subscription | Security policy view, policy compliance |
| **Policy Insights Data Writer (Reader)** | Subscription | Policy compliance reads |
| **Log Analytics Reader** | Log Analytics Workspace | Diagnostic settings verification |

> **Important**: The Service Principal MUST have at minimum **Reader** at subscription scope
> for subscription-level audit. Resource group-level audit works with Reader on that RG.

## Environment Setup

```bash
# Required environment variables
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-sp-app-id"
export AZURE_CLIENT_SECRET="your-sp-password"

# Verify credentials
az login --service-principal \
  --username "$AZURE_CLIENT_ID" \
  --password "$AZURE_CLIENT_SECRET" \
  --tenant "$AZURE_TENANT_ID"
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
az account show
```

## Install Dependencies

```bash
# Azure CLI (already installed in most Agent runtimes)
az --version

# Azure SDK for Python (fallback path)
pip install azure-identity azure-mgmt-monitor azure-mgmt-resource
pip install azure-mgmt-authorization azure-mgmt-policy azure-mgmt-storage
pip install azure-mgmt-compute azure-mgmt-network azure-mgmt-containerservice
```

## Python SDK Setup

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.authorization import AuthorizationManagementClient
import os

credential = DefaultAzureCredential()
subscription_id = os.environ.get('AZURE_SUBSCRIPTION_ID')

resource_client = ResourceManagementClient(credential, subscription_id)
monitor_client = MonitorManagementClient(credential, subscription_id)
auth_client = AuthorizationManagementClient(credential, subscription_id)
```

## Create Service Principal for Audit

```bash
# Create a read-only Service Principal for audit automation
az ad sp create-for-rbac \
  --name "azure-audit-sp" \
  --role Reader \
  --scopes "/subscriptions/{{subscription-id}}" \
  --output json
```

## Verify Prerequisites

```bash
# Quick connectivity and permission check
echo "=== Credentials ===" && az account show --query "{Sub:id, Tenant:tenantId}" -o tsv
echo "=== Activity Log ===" && az monitor activity-log list --max-events 1 -o tsv 2>/dev/null && echo "OK" || echo "FAIL"
echo "=== Role Assignments ===" && az role assignment list --max-items 1 -o tsv 2>/dev/null && echo "OK" || echo "FAIL"
echo "=== Resource Locks ===" && az lock list --max-items 1 -o tsv 2>/dev/null && echo "OK" || echo "FAIL"
echo "=== Policy ===" && az policy state list --max-items 1 -o tsv 2>/dev/null && echo "OK" || echo "FAIL"

## Full Audit Command Blocks

> Primary path is Azure CLI. On CLI failure, retry up to 3× (see azure-cli-conventions.md Retry
> Strategy), then fall back to the Azure SDK for Python snippets below. All commands are read-only.

### 1. Activity Log Review

```bash
# Recent subscription-level activity
az monitor activity-log list \
  --start-time "{{user.time_range_start}}" \
  --end-time "{{user.time_range_end}}" \
  --output json

# Filter by caller (user/SP)
az monitor activity-log list \
  --caller "{{user.caller_upn}}" \
  --start-time "{{user.time_range_start}}" \
  --end-time "{{user.time_range_end}}" \
  --output json

# Filter by operation
az monitor activity-log list \
  --operation "Microsoft.Compute/virtualMachines/write" \
  --start-time "{{user.time_range_start}}" \
  --output json

# Filter by resource group
az monitor activity-log list \
  --resource-group "{{user.resource_group}}" \
  --start-time "{{user.time_range_start}}" \
  --output json

# Filter by event severity
az monitor activity-log list \
  --severity Error \
  --start-time "{{user.time_range_start}}" \
  --output json

# Top-N summary: who did what, how many times
az monitor activity-log list \
  --start-time "{{user.time_range_start}}" \
  --query "[].{Caller:caller, Operation:operationName.value, Time:eventTimestamp}" \
  --output json
```

#### Azure SDK (Fallback)

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.monitor import MonitorManagementClient
from datetime import datetime, timedelta
import os

credential = DefaultAzureCredential()
client = MonitorManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

end_time = datetime.utcnow()
start_time = end_time - timedelta(days=7)

activity_log = client.activity_logs.list(
    filter=f"eventTimestamp ge '{start_time.isoformat()}Z' and eventTimestamp le '{end_time.isoformat()}Z'",
    select='caller,operationName,eventTimestamp,status'
)

for event in activity_log:
    print(f"{event.caller}: {event.operation_name.value} @ {event.event_timestamp}")
```

#### Validate / Recover

```bash
# Verify query returned data
az monitor activity-log list --max-events 1 --output json
```

| Error | Action |
|-------|--------|
| InvalidTimeRange | Fix time format; retry once |
| Throttling (429) | Backoff, retry 3× |
| 5xx Internal | Retry 3×, then HALT |

### 2. RBAC / Role Assignment Audit

```bash
az role assignment list --output json
az role assignment list --assignee "{{user.principal_id}}" --output json
az role assignment list --resource-group "{{user.resource_group}}" --output json
az role definition list --custom-role-only true --output json
az role assignment list --include-inherited \
  --query "[?roleDefinitionName=='Owner' || roleDefinitionName=='Contributor']" \
  --output json
```

### 3. Resource Lock Audit

```bash
az lock list --output json
az lock list --resource-group "{{user.resource_group}}" --output json
az lock list --resource "{{user.target_resource_id}}" --output json

# Find resources without locks (cross-check per RG)
az group list --query "[].name" -o tsv | while read rg; do
  locks=$(az lock list --resource-group "$rg" --query "length(@)" -o tsv)
  echo "$rg: $locks lock(s)"
done
```

### 4. Diagnostic Settings Completeness

```bash
az monitor diagnostic-settings list \
  --resource "{{user.target_resource_id}}" \
  --output json
# Find resources without diagnostic settings: iterate resources (SDK recommended at scale)
```

### 5. Policy Compliance

```bash
az policy assignment list --output json
az policy state list --output json
az policy state list \
  --filter "complianceState eq 'NonCompliant'" \
  --output json
az policy definition list --output json
az policy set-definition list --output json
```

### 6. Security Posture Review

```bash
# NSG rules with broad source access
az network nsg list --query "[].{Name:name, Rules:securityRules[?access=='Allow' && sourceAddressPrefix=='*' || sourceAddressPrefix=='Internet']}" --output json

# Storage accounts with public access allowed
az storage account list \
  --query "[?allowBlobPublicAccess==\`true\`].{Name:name, RG:resourceGroup}" \
  --output json

# VMs with public IPs (then check each NIC's IP config)
az vm list --query "[?networkProfile.networkInterfaces[?contains(id,'networkInterfaces')]].{Name:name, RG:resourceGroup}" --output json

# AKS clusters with RBAC disabled
az aks list --query "[?enableRBAC==\`false\`].{Name:name, RG:resourceGroup}" --output json

# SQL servers with firewall allowing all Azure services
az sql server firewall-rule list --server "{{user.sql_server}}" --resource-group "{{user.resource_group}}" \
  --query "[?startIpAddress=='0.0.0.0' && endIpActivity=='0.0.0.0']" --output json

# Key Vaults with soft-delete disabled
az keyvault list --query "[?enableSoftDelete==null || enableSoftDelete==\`false\`].{Name:name, RG:resourceGroup}" --output json
```

### 7. Resource Inventory & Configuration Drift

```bash
az resource list --output json
az resource list --resource-type "Microsoft.Compute/virtualMachines" --output json
az resource list --query "[?tags==null || !tags.Environment || !tags.Owner].{Name:name, Type:type, RG:resourceGroup}" --output json
az group list --query "[?tags==null || !tags.Environment].{Name:name, Location:location}" --output json
```
```