# Integration Setup — azure-cost-ops

## Required Permissions

| Role | Minimum Scope | Required For |
|------|--------------|--------------|
| **Cost Management Reader** | Subscription | Read cost data, query cost by service/RG/tag |
| **Cost Management Contributor** | Subscription | Create/edit/delete budgets |
| **Billing Reader** | Billing Account | Download invoices (EA/MCA) |
| **Reader** | Subscription | Read Advisor recommendations |

> **Tip**: For most cost analysis tasks, `Cost Management Reader` at subscription scope is sufficient.
> Budget management requires `Cost Management Contributor`.

## Environment Setup

```bash
# Required (minimum)
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-sp-app-id"
export AZURE_CLIENT_SECRET="your-sp-password"

# Required for EA/MCA billing (invoices, reservations)
export AZURE_BILLING_ACCOUNT_ID="your-billing-account-id"

# Verify
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
pip install azure-identity azure-mgmt-costmanagement
pip install azure-mgmt-consumption azure-mgmt-reservations
pip install azure-mgmt-billing
```

## Python SDK Setup

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.consumption import ConsumptionManagementClient
import os

credential = DefaultAzureCredential()
subscription_id = os.environ.get('AZURE_SUBSCRIPTION_ID')

cost_client = CostManagementClient(credential)
consumption_client = ConsumptionManagementClient(credential, subscription_id)

scope = f'/subscriptions/{subscription_id}'
```

## Create Service Principal for Cost Management

```bash
# Create a cost-management Service Principal
az ad sp create-for-rbac \
  --name "azure-cost-sp" \
  --role "Cost Management Reader" \
  --scopes "/subscriptions/{{subscription-id}}" \
  --output json

# For budget management, add Contributor
az role assignment create \
  --assignee "{{sp-object-id}}" \
  --role "Cost Management Contributor" \
  --scope "/subscriptions/{{subscription-id}}"
```

## Find Billing Account ID (EA/MCA)

```bash
# List billing accounts
az billing account list --output json

# Look for the "id" field — e.g. /providers/Microsoft.Billing/billingAccounts/{id}
# Set it as AZURE_BILLING_ACCOUNT_ID
```

## Find Subscription ID

```bash
# List subscriptions
az account list --output json

# Set active subscription
az account set --subscription "{{subscription-id}}"
```

## Quick Verification

```bash
echo "=== Cost Management ==="
az costmanagement query --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "ServiceName" type "Dimension" \
  --output json --query "rows[0:1]" 2>/dev/null && echo "OK" || echo "FAIL"

echo "=== Budget ==="
az consumption budget list \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --output json 2>/dev/null && echo "OK" || echo "FAIL"
```