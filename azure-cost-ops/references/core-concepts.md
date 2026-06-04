# Core Concepts — azure-cost-ops

> Azure Cost Management and Billing concepts.

## Cost Management Scopes

| Scope | CLI Usage | Data Available |
|-------|-----------|----------------|
| **Subscription** | `/subscriptions/{id}` | Pay-as-you-go, MCA billing |
| **Resource Group** | `/subscriptions/{id}/resourceGroups/{name}` | RG-level rollup |
| **Management Group** | `/providers/Microsoft.Management/managementGroups/{id}` | Multi-subscription rollup |
| **Billing Account** | `/providers/Microsoft.Billing/billingAccounts/{id}` | EA/MCA full billing data |
| **Billing Profile** | `/providers/Microsoft.Billing/billingAccounts/{id}/billingProfiles/{id}` | MCA invoice section |

**Important**: For subscription-based costs, use the subscription scope. For EA/MCA billing,
you need the billing account scope and the `AZURE_BILLING_ACCOUNT_ID` env var.

## Cost Types

| Type | Description | CLI Flag |
|------|-------------|----------|
| **ActualCost** | Actual charges incurred | `--type ActualCost` |
| **AmortizedCost** | Amortized reservation/savings plan costs | `--type AmortizedCost` |
| **Forecast** | Predicted cost | `--include-forecast` (with query) |

## Billing Models

| Model | Entity | Invoice Cycle | API Support |
|-------|--------|--------------|-------------|
| **Pay-as-you-go (PAYG)** | Subscription | Monthly | `az costmanagement`, `az consumption` |
| **Enterprise Agreement (EA)** | Billing Account | Quarterly/Monthly | `az billing invoice` |
| **Microsoft Customer Agreement (MCA)** | Billing Profile | Monthly | `az billing invoice` |

## Budget Types

| Budget | Description | CLI |
|--------|-------------|-----|
| **Cost Budget** | Track spending against a threshold | `az consumption budget` |
| **Reservation Budget** | Track reservation utilization | N/A (via Cost Management API) |

## Reservation / Savings Plan

| Offering | Discount Type | Term | Management |
|----------|--------------|------|------------|
| **Reserved Instance** | 1yr/3yr commit for specific VM size | 1 or 3 years | `az reservations reservation` |
| **Savings Plan** | 1yr/3yr commit for compute $ amount | 1 or 3 years | `az billing savings-plan` |

## Cost Optimization Pillars (FinOps)

| Pillar | Description | Tools |
|--------|-------------|-------|
| **Visibility** | Know what you're spending | Cost Management, Budgets |
| **Optimization** | Reduce waste | Advisor, Right-sizing |
| **Rate Optimization** | Get best prices | Reservations, Savings Plans |
| **Governance** | Control spending | Budgets, Policies, Locks |

## Key Metrics

| Metric | Query | Purpose |
|--------|-------|---------|
| Cost by service | `--dataset-grouping name "ServiceName"` | Which services cost the most |
| Cost by resource group | `--dataset-grouping name "ResourceGroupName"` | Cost per team/project |
| Cost by tag | `--dataset-grouping name "TagKey"` | Chargeback/showback |
| Month-over-month | Two queries with different timeframes | Trending |
| Forecast | `--include-forecast` | Predict end-of-month cost |
| Reservation utilization | `az reservations reservation list` | Are RIs being used? |

## Required RBAC Roles

| Role | Scope | Operations |
|------|-------|-----------|
| Cost Management Reader | Subscription / RG | Read cost data |
| Cost Management Contributor | Subscription / RG | Read + create budgets |
| Reader | Subscription | Read Advisor recommendations |
| Billing Reader | Billing Account | Read invoices (EA/MCA) |