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

Primary CLI: `az costmanagement query --type ActualCost --timeframe MonthToDate --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" --dataset-grouping name ServiceName type Dimension --output json`. Variants (by RG / Resource / Tag / Location, custom time, forecast) + SDK fallback: see [references/integration.md](references/integration.md). Recover: `AuthorizationFailed` → HALT (assign Cost Management Reader); `ProviderNotRegistered` → HALT (register `Microsoft.CostManagement`); throttling/5xx → retry 3× then HALT.

## Operation: Budget Management

`az consumption budget list / show` for read. Full `budget create` command (Cost Management Contributor required): see [references/integration.md](references/integration.md).

**Safety Gate — Budget delete (required, GCL required)**: show the budget first, then require explicit human confirmation before `az consumption budget delete`. Safety=0 → ABORT.

## Operation: Reservation & Savings Plan

`az reservations reservation list ...` for utilization review. Full commands (recommendations, savings-plan list, reservation-order): see [references/integration.md](references/integration.md).

## Operation: Invoice Management

`az billing invoice list / download`. Full commands (MCA billing profile, EA billing account variants): see [references/integration.md](references/integration.md). Billing Reader role required.

## Operation: Cost Optimization Recommendations

`az advisor recommendation list --query "[?category=='Cost']"` for cost advice. Right-sizing / idle-resource queries: see [references/integration.md](references/integration.md).

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

## L4 Auto-Feedback Loop

For autonomous operation, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-cost-ops \
  --operation cost_query \
  --command "az costmanagement query ..." \
  --desired-state '{}' \
  [--dry-run] [--trace-id <uuid>]
```

- Read-only operations (cost_query): auto-feedback loop active
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md) — scopes, billing models, FinOps pillars, RBAC roles
- [Troubleshooting](references/troubleshooting.md) — error codes, recovery
- [Integration Setup](references/integration.md) — full CLI/SDK commands, env setup, RBAC
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

See [Core Concepts](references/core-concepts.md) for scopes, billing models, and FinOps pillars.
