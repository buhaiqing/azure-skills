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
```