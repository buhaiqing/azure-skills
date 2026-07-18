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

## Full Command Reference

> Moved here from `SKILL.md` to keep the entrypoint slim. All commands use
> `--scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}"` unless noted.

### Cost Analysis (`az costmanagement query`)

```bash
# Cost by resource group (current month to date)
az costmanagement query \
  --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "ResourceGroupName" type "Dimension" --output json

# Cost by resource (current month)
az costmanagement query \
  --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "ResourceName" type "Dimension" --output json

# Cost by service name (current month)
az costmanagement query \
  --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "ServiceName" type "Dimension" --output json

# Cost by tag (current month)
az costmanagement query \
  --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "TagKey" type "Dimension" --output json

# Cost by location
az costmanagement query \
  --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "Location" type "Dimension" --output json

# Custom time range
az costmanagement query \
  --type ActualCost --timeframe Custom \
  --time-period from "2026-05-01" to "2026-05-31" \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "ServiceName" type "Dimension" --output json

# Filter by resource group
az costmanagement query \
  --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-filter "{\"dimensions\":[{\"name\":\"ResourceGroupName\",\"operator\":\"In\",\"values\":[\"{{user.resource_group}}\"]}]}" \
  --dataset-grouping name "ResourceName" type "Dimension" --output json

# Forecast (predicted cost for current month)
az costmanagement query \
  --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --include-forecast \
  --dataset-grouping name "ServiceName" type "Dimension" --output json
```

#### Azure SDK (Fallback)

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.costmanagement import CostManagementClient
import os

credential = DefaultAzureCredential()
client = CostManagementClient(credential)

response = client.query.usage(
    scope=f'/subscriptions/{os.environ.get("AZURE_SUBSCRIPTION_ID")}',
    parameters={
        'type': 'ActualCost',
        'timeframe': 'MonthToDate',
        'dataset': {
            'granularity': 'Daily',
            'grouping': [{'name': 'ServiceName', 'type': 'Dimension'}]
        }
    }
)

for row in response.rows:
    print(f"{row[0]}: {row[1]} {row[2]}")
```

#### Validate

```bash
az costmanagement query --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "ServiceName" type "Dimension" \
  --output json --query "rows" | head -5
```

### Budget Management (`az consumption budget`)

```bash
# List budgets
az consumption budget list \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" --output json

# Show specific budget
az consumption budget show \
  --budget-name "{{user.budget_name}}" \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" --output json

# Create budget with notification (Cost Management Contributor required)
az consumption budget create \
  --budget-name "{{user.budget_name}}" \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --amount "{{user.budget_amount}}" \
  --time-grain Monthly \
  --time-period start-date "{{user.budget_start}}" end-date "{{user.budget_end}}" \
  --category Cost \
  --notification-group threshold-type Actual,Percent \
  --notification-group threshold 80,100 \
  --notification-group operator GreaterThan \
  --notification-group email "{{user.alert_email}}" \
  --notification-group enabled true --output json

# Delete budget — SAFETY GATE: confirm with human before running
az consumption budget delete \
  --budget-name "{{user.budget_name}}" \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" --output json
```

### Reservation & Savings Plan

```bash
# List reservations
az reservations reservation list \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" --output json

# Reservation utilization
az reservations reservation list \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --query "[].{Name:name, Utilization:properties.utilization, Sku:sku.name}" --output json

# Reservation recommendations
az reservations reservation-order list --output json

# Savings plan list (EA/MCA)
az billing savings-plan list \
  --billing-account-name "{{env.AZURE_BILLING_ACCOUNT_ID}}" --output json
```

### Invoice Management

```bash
# List invoices (Enterprise Agreement)
az billing invoice list \
  --billing-account-name "{{env.AZURE_BILLING_ACCOUNT_ID}}" --output json

# Download invoice (EA)
az billing invoice download \
  --billing-account-name "{{env.AZURE_BILLING_ACCOUNT_ID}}" \
  --invoice-name "{{user.invoice_name}}" --download-urls --output json

# List invoices for MCA (Microsoft Customer Agreement)
az billing invoice list \
  --billing-profile-name "{{user.billing_profile}}" \
  --billing-account-name "{{env.AZURE_BILLING_ACCOUNT_ID}}" --output json
```

### Cost Optimization Recommendations

```bash
# Right-sizing recommendations (requires Azure Advisor)
az advisor recommendation list --query "[?category=='Cost']" --output json

# Idle resources (requires Azure Advisor)
az advisor recommendation list \
  --query "[?category=='Cost' && (contains(impactedField,'VirtualMachine') || contains(impactedField,'Storage'))]" \
  --output json

# Under-utilized resources
az monitor metrics list \
  --resource "{{user.target_resource_id}}" --metric "Percentage CPU" \
  --interval PT1H --aggregation Average --top 168 --orderby Average desc --output json
```
```