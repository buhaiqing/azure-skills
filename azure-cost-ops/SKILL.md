---
name: azure-cost-ops
description: >-
  Use when analyzing Azure costs, querying billing data, managing budgets,
  reviewing invoices, or optimizing cloud spending. User mentions "cost",
  "billing", "spending", "budget", "invoice", "reservation", "savings plan",
  "cost analysis", "FinOps", "chargeback", or "cost optimization".
license: MIT
compatibility: >-
  Azure CLI, Azure SDK for Python (3.10+), valid Azure credentials
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
- Task involves: cost analysis by resource/RG/tag, budget create/inspect/delete, invoice download, reservation/savings plan review
- Keywords: cost, billing, spending, budget, invoice, reservation, savings plan, FinOps, chargeback, showback, cost optimization, right-sizing, waste
- Monthly/quarterly cost review, cross-service cost comparison

### SHOULD NOT Use When
- Creating/modifying resources → delegate to: specific service skill
- Billing support tickets → delegate to: Azure Support (manual)
- Subscription cancellation → delegate to: Azure Portal (no CLI)
- Audit / RBAC / Policy → delegate to: `azure-audit-ops`

## Variable Convention

Auth env quad (`AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`) + pre-flight are common skeletons — see [Credential Sources & Priority Order](../../azure-skill-generator/references/azure-cli-conventions.md#credential-sources-priority-order). Business placeholders used in this skill:

- `{{user.resource_group}}` — cost by RG (ask once)
- `{{user.time_range}}` — e.g. "LastMonth", "2026-05-01/2026-05-31"
- `{{user.budget_name}}` — budget name for create/inspect/delete
- `{{user.budget_amount}}` — budget threshold amount
- `{{user.budget_start}}` / `{{user.budget_end}}` — budget period dates
- `{{user.alert_email}}` — budget notification email
- `{{user.billing_profile}}` — MCA billing profile name
- `{{user.invoice_name}}` — invoice to download
- `{{user.target_resource_id}}` — resource for utilization metrics
- `{{output.cost_summary}}` — parsed cost data from last query
- `{{output.budget_status}}` — budget spend vs threshold from last query

## Execution Flow Pattern

Every operation follows: **Scope → Query → Analyze → Report**. CLI is primary; on failure retry up to 3×, then fall back to Azure SDK for Python. Pre-flight checks and retry/backoff rules are shared skeletons — see [azure-cli-conventions.md](../../azure-skill-generator/references/azure-cli-conventions.md).

```
┌─────────┐    ┌─────────┐    ┌──────────┐    ┌─────────┐
│  Scope  │ →  │  Query  │ →  │ Analyze  │ →  │ Report  │
│ Definition│   │  Data   │    │ Findings │    │ & Actions│
└─────────┘    └─────────┘    └──────────┘    └─────────┘
```

**RBAC note**: read cost data needs **Cost Management Reader**; budget create/delete needs **Cost Management Contributor**; invoice download (EA/MCA) needs **Billing Reader**. See [integration.md](references/integration.md) for setup.

## Operation: Cost Analysis

Primary CLI (cost by service, current month to date):

```bash
az costmanagement query \
  --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "ServiceName" type "Dimension" \
  --output json
```

Variants (by ResourceGroupName / ResourceName / TagKey / Location, custom time range, RG filter, `--include-forecast`) and the Azure SDK fallback are in [integration.md](references/integration.md). Recover: `AuthorizationFailed` → HALT, assign Cost Management Reader; `ProviderNotRegistered` → HALT, register `Microsoft.CostManagement`; throttling/5xx → retry 3× then HALT. Full error table in [troubleshooting.md](references/troubleshooting.md).

## Operation: Budget Management

```bash
az consumption budget list --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" --output json
az consumption budget show --budget-name "{{user.budget_name}}" \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" --output json
# Create (Cost Management Contributor required):
az consumption budget create --budget-name "{{user.budget_name}}" \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" --amount "{{user.budget_amount}}" \
  --time-grain Monthly --time-period start-date "{{user.budget_start}}" end-date "{{user.budget_end}}" \
  --category Cost --notification-group threshold-type Actual,Percent \
  --notification-group threshold 80,100 --notification-group operator GreaterThan \
  --notification-group email "{{user.alert_email}}" --notification-group enabled true --output json
```

**Safety Gate — Budget delete (required, GCL required)**: show the budget first, then require explicit human confirmation before `az consumption budget delete`. Safety=0 → ABORT.

## Operation: Reservation & Savings Plan

```bash
az reservations reservation list --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" --output json
az reservations reservation list --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --query "[].{Name:name, Utilization:properties.utilization, Sku:sku.name}" --output json
az billing savings-plan list --billing-account-name "{{env.AZURE_BILLING_ACCOUNT_ID}}" --output json
```

Full command set (recommendations, reservation-order) in [integration.md](references/integration.md).

## Operation: Invoice Management

```bash
az billing invoice list --billing-account-name "{{env.AZURE_BILLING_ACCOUNT_ID}}" --output json
az billing invoice download --billing-account-name "{{env.AZURE_BILLING_ACCOUNT_ID}}" \
  --invoice-name "{{user.invoice_name}}" --download-urls --output json
# MCA: add --billing-profile-name "{{user.billing_profile}}"
```

Billing Reader role required for EA/MCA. Full set in [integration.md](references/integration.md).

## Operation: Cost Optimization Recommendations

```bash
az advisor recommendation list --query "[?category=='Cost']" --output json
az monitor metrics list --resource "{{user.target_resource_id}}" --metric "Percentage CPU" \
  --interval PT1H --aggregation Average --top 168 --orderby Average desc --output json
```

Right-sizing / idle-resource queries in [integration.md](references/integration.md).

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate. See `AGENTS.md §3–§8` for the spec.

| Parameter | Value |
|-----------|-------|
| GCL | **recommended** (read-only queries) / **required** (budget create/delete) |
| max_iterations | 3 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- Cost analysis queries → recommended
- Budget create/modify → **required** (amount + notification email confirmed)
- Budget delete → **required**; Safety=0 → ABORT
- Invoice download → recommended
- Reservation/savings plan operations → recommended

## Reference Files

- [Core Concepts](references/core-concepts.md) — scopes, billing models, FinOps pillars, RBAC roles
- [Troubleshooting](references/troubleshooting.md) — error codes, recovery
- [Integration Setup](references/integration.md) — full CLI/SDK commands, env setup, RBAC
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Cost Management Docs](https://learn.microsoft.com/azure/cost-management-billing/)
- [Azure CLI Cost Management](https://learn.microsoft.com/cli/azure/costmanagement)
- [Azure CLI Consumption](https://learn.microsoft.com/cli/azure/consumption)
- [FinOps Framework](https://www.finops.org/)
