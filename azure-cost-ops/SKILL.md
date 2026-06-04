---
name: azure-cost-ops
description: >-
  Use when analyzing Azure costs, querying billing data, managing budgets,
  reviewing invoices, or optimizing cloud spending. User mentions "cost",
  "billing", "spending", "budget", "invoice", "reservation", "savings plan",
  "cost analysis", "FinOps", "chargeback", or "cost optimization".
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials
  (Cost Management Reader role or higher), network access to Azure endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
    - AZURE_BILLING_ACCOUNT_ID (optional, for Enterprise Agreement billing)
---

# Azure Cost Operations Skill

## Overview

Azure Cost Management provides tools for monitoring, analyzing, and optimizing cloud spending.
This skill is an **operational runbook** for cost/billing read operations and budget management.
It does NOT modify resource configurations (use the specific service skill for that).

## Trigger & Scope

### SHOULD Use When
- User mentions "Az cost", "billing", "spending", "budget", "invoice", "FinOps"
- Task involves: cost analysis by resource/RG/tag, budget creation, invoice download, reservation/savings plan review
- Keywords: cost, billing, spending, budget, invoice, reservation, savings plan, FinOps, chargeback, showback, cost optimization, right-sizing, waste
- Monthly/quarterly cost review
- Cross-service cost comparison

### SHOULD NOT Use When
- Creating/modifying resources → delegate to: specific service skill
- Billing support tickets → delegate to: Azure Support (manual)
- Subscription cancellation → delegate to: Azure Portal (no CLI)
- Audit / RBAC / Policy → delegate to: `azure-audit-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_BILLING_ACCOUNT_ID}}` | Runtime env | Required only for EA billing scope |
| `{{user.resource_group}}` | User input | Cost by RG; ask once |
| `{{user.time_range}}` | User input | e.g. "LastMonth", "2026-05-01/2026-05-31" |
| `{{user.budget_name}}` | User input | Budget name for create/inspect |
| `{{user.budget_amount}}` | User input | Budget threshold amount |
| `{{output.cost_summary}}` | Last API response | Parsed cost data |
| `{{output.budget_status}}` | Last API response | Budget current spend vs threshold |

## Execution Flow Pattern

Every operation follows: **Scope → Query → Analyze → Report**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Scope     │ → │   Query     │ → │   Analyze   │ → │   Report    │
│  Definition │    │    Data     │    │   Findings  │    │  & Actions  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Cost Analysis

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show` | HALT; configure env |
| Subscription valid | `az account list --output json` | Suggest valid subscription |
| Cost Management provider | `az provider show --namespace Microsoft.CostManagement` | HALT; register provider |

#### Execute — Azure CLI (Primary)
```bash
# Cost by resource group (current month to date)
az costmanagement query \
  --type ActualCost \
  --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "ResourceGroupName" type "Dimension" \
  --output json

# Cost by resource (current month)
az costmanagement query \
  --type ActualCost \
  --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "ResourceName" type "Dimension" \
  --output json

# Cost by service name (current month)
az costmanagement query \
  --type ActualCost \
  --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "ServiceName" type "Dimension" \
  --output json

# Cost by tag (current month)
az costmanagement query \
  --type ActualCost \
  --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "TagKey" type "Dimension" \
  --output json

# Cost by location / region
az costmanagement query \
  --type ActualCost \
  --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "Location" type "Dimension" \
  --output json

# Custom time range
az costmanagement query \
  --type ActualCost \
  --timeframe Custom \
  --time-period from "2026-05-01" to "2026-05-31" \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "ServiceName" type "Dimension" \
  --output json

# Filter by resource group
az costmanagement query \
  --type ActualCost \
  --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-filter "{\"dimensions\":[{\"name\":\"ResourceGroupName\",\"operator\":\"In\",\"values\":[\"{{user.resource_group}}\"]}]}" \
  --dataset-grouping name "ResourceName" type "Dimension" \
  --output json

# Forecast (predicted cost for current month)
az costmanagement query \
  --type ActualCost \
  --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --include-forecast \
  --dataset-grouping name "ServiceName" type "Dimension" \
  --output json
```

#### Execute — Azure SDK (Fallback)
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.costmanagement import CostManagementClient
import os

credential = DefaultAzureCredential()
client = CostManagementClient(credential)

# Query cost by service
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
# Verify query returned data
az costmanagement query --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "ServiceName" type "Dimension" \
  --output json --query "rows" | head -5
```

#### Recover
| Error | Action |
|-------|--------|
| 403 Forbidden | HALT; assign Cost Management Reader role |
| ProviderNotRegistered | HALT; run `az provider register --namespace Microsoft.CostManagement` |
| InvalidTimeframe | Fix timeframe; retry once |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |

### Operation: Budget Management

```bash
# List budgets
az consumption budget list \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --output json

# Show specific budget
az consumption budget show \
  --budget-name "{{user.budget_name}}" \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --output json

# Create budget with notification
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
  --notification-group enabled true \
  --output json

# Delete budget (Safety Gate required)
az consumption budget show \
  --budget-name "{{user.budget_name}}" \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --output json

# After confirmation:
az consumption budget delete \
  --budget-name "{{user.budget_name}}" \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --output json
```

### Operation: Reservation & Savings Plan

```bash
# List reservations
az reservations reservation list \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --output json

# Reservation utilization
az reservations reservation list \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --query "[].{Name:name, Utilization:properties.utilization, Sku:sku.name}" \
  --output json

# Reservation recommendations
az reservations reservation-order list --output json

# Savings plan list
az billing savings-plan list \
  --billing-account-name "{{env.AZURE_BILLING_ACCOUNT_ID}}" \
  --output json
```

### Operation: Invoice Management

```bash
# List invoices (Enterprise Agreement)
az billing invoice list \
  --billing-account-name "{{env.AZURE_BILLING_ACCOUNT_ID}}" \
  --output json

# Download invoice (EA)
az billing invoice download \
  --billing-account-name "{{env.AZURE_BILLING_ACCOUNT_ID}}" \
  --invoice-name "{{user.invoice_name}}" \
  --download-urls \
  --output json

# List invoices for MCA (Microsoft Customer Agreement)
az billing invoice list \
  --billing-profile-name "{{user.billing_profile}}" \
  --billing-account-name "{{env.AZURE_BILLING_ACCOUNT_ID}}" \
  --output json
```

### Operation: Cost Optimization Recommendations

```bash
# Right-sizing recommendations (requires Azure Advisor)
az advisor recommendation list \
  --query "[?category=='Cost']" \
  --output json

# Idle resources (requires Azure Advisor)
az advisor recommendation list \
  --query "[?category=='Cost' && (contains(impactedField,'VirtualMachine') || contains(impactedField,'Storage'))]" \
  --output json

# Under-utilized resources
az monitor metrics list \
  --resource "{{user.target_resource_id}}" \
  --metric "Percentage CPU" \
  --interval PT1H \
  --aggregation Average \
  --top 168 \
  --orderby Average desc \
  --output json
```

## Cost Dimensions

| Dimension | Description | CLI Parameter |
|-----------|-------------|---------------|
| ServiceName | Azure service (VM, Storage, etc.) | `--dataset-grouping name "ServiceName" type "Dimension"` |
| ResourceGroupName | Resource group | `--dataset-grouping name "ResourceGroupName" type "Dimension"` |
| ResourceName | Individual resource | `--dataset-grouping name "ResourceName" type "Dimension"` |
| Location | Azure region | `--dataset-grouping name "Location" type "Dimension"` |
| TagKey | Custom tag | `--dataset-grouping name "TagKey" type "Dimension"` |
| MeterCategory | Meter category | `--dataset-grouping name "MeterCategory" type "Dimension"` |

## Timeframes

| Timeframe | Description |
|-----------|-------------|
| MonthToDate | Current month, partial |
| BillingMonthToDate | Current billing period |
| TheLastMonth | Previous complete month |
| TheLastBillingMonth | Previous complete billing period |
| WeekToDate | Current week, partial |
| Custom | Custom start/end date in YYYY-MM-DD format |

## Report Template

| Dimension | Period | Cost | % of Total | Previous Period | Change |
|-----------|--------|------|------------|-----------------|--------|
| ServiceName: Virtual Machines | 2026-05 | $1,234.56 | 45% | $1,100.00 | +12.2% |
| ServiceName: Storage | 2026-05 | $456.78 | 17% | $420.00 | +8.7% |
| ServiceName: Networking | 2026-05 | $345.67 | 13% | $350.00 | -1.2% |

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate.
See `AGENTS.md §3–§8` for the spec.

| Parameter | Value |
|-----------|-------|
| GCL | **recommended** (read-only queries — GCL recommended but not required) |
| max_iterations | 3 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- Cost analysis queries → recommended
- Budget creation/modification → **required** (budget amount and notification email confirmed)
- Budget delete → **required**; Safety=0 → ABORT
- Invoice download → recommended
- Reservation/savings plan operations → recommended

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Cost Management Docs](https://docs.microsoft.com/azure/cost-management-billing/)
- [Azure CLI Cost Management](https://docs.microsoft.com/cli/azure/costmanagement)
- [Azure CLI Consumption](https://docs.microsoft.com/cli/azure/consumption)
- [FinOps Framework](https://www.finops.org/)