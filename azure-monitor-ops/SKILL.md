---
name: azure-monitor-ops
description: >-
  Use when operating Azure Monitor resources via Azure CLI or Azure SDK;
  user mentions "Monitor", "Metrics", "Alerts", "Log Analytics", "Application Insights",
  "Activity Log", or monitoring/alerting scenarios.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints.
metadata:
  author: azure
  version: "1.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Monitor Operations Skill

## Overview

Azure Monitor provides comprehensive monitoring, diagnostics, and alerting for Azure resources and applications. This skill is an operational runbook: explicit scope, credential rules, dual-path execution (Azure CLI + Azure SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure Monitor", "Metrics", "Alerts", "Log Analytics", "Application Insights", "Activity Log"
- Task involves monitoring configuration, alert setup, log queries, metric retrieval
- Keywords: monitor, metric, alert, log analytics, application insights, diagnostic setting, activity log, action group, alert rule
- Resource health checks, performance monitoring, diagnostic configuration

### SHOULD NOT Use When
- Billing only → delegate to: `azure-cost-ops`
- RBAC/IAM only → delegate to: `azure-rbac-ops`
- Resource creation (compute/storage) → delegate to: specific service skill
- Network configuration → delegate to: `azure-network-ops`

## Variable Convention

Auth env quad (`{{env.AZURE_SUBSCRIPTION_ID}}`, `{{env.AZURE_TENANT_ID}}`, `{{env.AZURE_CLIENT_ID}}`, `{{env.AZURE_CLIENT_SECRET}}`) is a common skeleton — never ask the user; fail if unset. Full credential-sources priority order: [azure-cli-conventions.md#credential-sources-priority-order](../../azure-skill-generator/references/azure-cli-conventions.md#credential-sources-priority-order).

Business placeholders (ask once, reuse):
- `{{user.resource_group}}` — target Resource Group
- `{{user.target_resource_id}}` — resource being monitored
- `{{user.action_group_name}}` — action group name for alerts
- `{{user.alert_rule_name}}` — alert rule name
- `{{user.workspace_id}}` / `{{user.log_analytics_workspace_id}}` — Log Analytics workspace
- `{{user.diagnostic_setting_name}}` — diagnostic setting name

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

Pre-flight checks (env resolution, retry policy, credential priority) and the 3× CLI-retry-then-SDK fallback are defined in [azure-cli-conventions.md](../../azure-skill-generator/references/azure-cli-conventions.md).

## Operations

All operations are dual-path (Azure CLI primary + Azure SDK fallback). Full `az monitor ...` command blocks, SDK snippets, and KQL are in [integration.md](references/integration.md). Monitor components, alert types, and KQL basics are in [core-concepts.md](references/core-concepts.md).

### Metrics
```bash
az monitor metrics list --resource "{{user.target_resource_id}}" --output json
```
Full metric retrieval (CLI + SDK) → [integration.md §1](references/integration.md).

### Alerts (Action Groups + Alert Rules)
```bash
# Metric alert
az monitor metrics alert create --name "{{user.alert_rule_name}}" \
  --resource-group "{{user.resource_group}}" --scopes "{{user.target_resource_id}}" \
  --condition "avg Percentage CPU > 80" --action "{{user.action_group_name}}" --output json
# Log alert (scheduled query)
az monitor scheduled-query create --name "{{user.alert_rule_name}}" \
  --resource-group "{{user.resource_group}}" --scopes "{{user.log_analytics_workspace_id}}" \
  --condition-query "AzureActivity | where OperationName == 'RestartVM'" --action "{{user.action_group_name}}" --output json
```
Action group create + both alert types (CLI) → [integration.md §2–§4](references/integration.md).

### Log Analytics
```bash
az monitor log-analytics query --workspace "{{user.workspace_id}}" \
  --analytics-query "AzureActivity | take 10" --timespan "1d" --output json
```
Query + SDK + KQL examples → [integration.md §5](references/integration.md).

### Diagnostic Settings
```bash
az monitor diagnostic-settings create --name "{{user.diagnostic_setting_name}}" \
  --resource "{{user.target_resource_id}}" --workspace "{{user.workspace_id}}" --output json
```
Full diagnostic-settings create (logs/metrics) → [integration.md §6](references/integration.md).

### Activity Log
```bash
az monitor activity-log list --resource "{{user.target_resource_id}}" --output json
```
Caller / event-name variants → [integration.md §7](references/integration.md).

## Safety Gates (Destructive)

- **Delete Alert Rule**: show rule first, then require exact alert rule name. GCL required.
- **Delete Action Group**: list rules referencing it first, then require confirmation. GCL required.
- **Delete Diagnostic Setting**: warn of data-flow gap (logs/metrics stop streaming). GCL required.

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate. See `AGENTS.md §3–§8` for the spec.

| Parameter | Value |
|-----------|-------|
| GCL | **recommended** |
| max_iterations | 3 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE alert rule (`az monitor metrics alert delete`) → **required**; monitoring gap warning + Safety=0 → ABORT
- DELETE action group (`az monitor action-group delete`) → **required**; check rule references + affected rules listed
- DELETE diagnostic setting → **required**; data flow gap communicated
- CREATE alert rule / action group / diagnostic setting → recommended
- QUERY metrics / logs / activity log (read-only) → optional (GCL may be skipped)

### Read-Only vs Write
Most Monitor operations are read-only (query, list, show). GCL is encouraged but not required for read-only operations. All **delete** operations are required to go through GCL.

## L4 Auto-Feedback Loop

For autonomous operation on non-risky operations, wrap skill execution with the L4 auto-feedback loop:
```bash
python scripts/auto_feedback_loop.py \
  --skill azure-monitor-ops \
  --operation alert_rule_create \
  --command "az monitor alert rule create --name {{user.rule_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"provisioningState": "Succeeded"}' \
  [--dry-run] [--trace-id <uuid>]
```
- **Non-risky operations** (alert_rule_create, action_group_create): auto-feedback loop active
- **Risky operations** (delete): always bypass loop and require explicit human confirmation
- Healing policy: see [`scripts/self_healing/monitor_heal.json`](../../scripts/self_healing/monitor_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md) — Monitor components, alert types, KQL basics
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md) — full `az monitor` commands, SDK snippets, KQL
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)



> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
