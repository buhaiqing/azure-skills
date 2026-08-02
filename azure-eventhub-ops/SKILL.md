---
name: azure-eventhub-ops
description: >-
  Use when operating or diagnosing Azure Event Hubs resources. User mentions
  Event Hubs, event hub, Kafka endpoint, throughput unit (TU), processing unit
  (PU), Capture, event streaming, consumer group, partition, or Event Hubs
  AIOps/RCA (throttling, partition skew, consumer lag, Capture failure).
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials,
  network access to Azure management endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-07-11"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Event Hubs Operations Skill

## Overview

Azure Event Hubs provides managed event streaming (AMQP, Kafka). This skill handles Event Hubs namespace and event hub operations, throughput management, Capture configuration, safe diagnostics, AIOps-assisted incident analysis, and root-cause investigation. Keep this file concise; load reference files for commands, SDK patterns, RCA rules, and detailed scenarios.

## Trigger & Scope

### SHOULD Use When
- User mentions Event Hubs, event hub, Kafka endpoint, TU/PU, Capture, or consumer group.
- Task involves namespace/event hub/consumer group create/show/list/update/delete, throughput scaling, Capture toggle, authorization rule management, or access key rotation.
- User asks for AIOps analysis: throughput throttling, partition skew, consumer lag, Capture failures.

### SHOULD NOT Use When
- Billing/cost only → delegate to `azure-cost-ops`.
- Cross-product audit, RBAC, locks, policy, or Activity Log-only analysis → delegate to `azure-audit-ops`.
- Generic metrics/log query authoring → delegate to `azure-monitor-ops`.
- Capture storage detail (Blob Storage account) → delegate to `azure-blobstorage-ops`.
- Azure Function trigger setup → delegate to `azure-function-ops`.
- VNet/Private Link deep dive not specific to Event Hubs → provide entry diagnostics, then escalate to network owner.

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; required for resource operations |
| `{{user.location}}` | User input | Azure Location, e.g. `eastus`; validate before create |
| `{{user.namespace_name}}` | User input | Event Hubs namespace name; ask once |
| `{{user.eventhub_name}}` | User input | Event hub name within namespace |
| `{{user.consumer_group_name}}` | User input | Default `$Default`; override as needed |
| `{{user.sku}}` | User input | `Basic`, `Standard`, `Premium`, `Dedicated` |
| `{{user.throughput_units}}` | User input | TU count (1-20 for Standard, auto-inflate) |
| `{{user.partition_count}}` | User input | 1-32 for Standard; 1-maxPerSKU for others |
| `{{user.message_retention_days}}` | User input | Default 7; 1-7 for Standard, up to 90 for Premium/Dedicated |
| `{{user.rule_name}}` | User input | Authorization rule name, e.g. RootManageSharedAccessKey; ask once |
| `{{user.analysis_window}}` | User input | Default `PT1H`; use `PT6H`/`P1D` for incidents |
| `{{output.namespace_id}}` | CLI/SDK output | Parse from `.id` |
| `{{output.eventhub_id}}` | CLI/SDK output | Parse from `.id` |
| `{{output.metric_window}}` | Monitor output | Parsed anomaly window |

## JSON Paths

| Key | Path |
|-----|------|
| NAMESPACE_ID / EVENTHUB_ID / CONSUMER_GROUP_ID | `.id` |
| NAMESPACE_STATE | `.properties.provisioningState` |
| NAMESPACE_SKU | `.sku.name` |
| NAMESPACE_TU | `.sku.capacity` |
| NAMESPACE_ENDPOINT | `.properties.serviceBusEndpoint` |
| EVENTHUB_PARTITIONS | `.properties.partitionCount` |
| EVENTHUB_STATE | `.properties.status` |
| CONNECTION_STRING | `.connectionString` |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover → Report**.

| Phase | Required Actions |
|-------|------------------|
| Pre-flight | Verify CLI, credentials, subscription, Resource Group, Location, provider `Microsoft.EventHub`, RBAC, and target resource state. |
| Execute | Use Azure CLI primary. Retry transient CLI failures up to 3x with backoff before SDK fallback. |
| Validate | Confirm provisioning/state/metric result with `--output json`; poll LRO every 30s, max 30m unless reference says otherwise. |
| Recover | Apply HALT-vs-retry matrix; never guess fields or retry destructive actions blindly. |
| Report | Return evidence, confidence, safe next actions, and actions requiring confirmation. |

## Operation Map

| Intent | Primary CLI | Reference |
|--------|-------------|-----------|
| Namespace create/show/list/update/delete | `az eventhubs namespace` | [integration.md](references/integration.md) |
| Event hub create/show/list/update/delete | `az eventhubs eventhub` | [integration.md](references/integration.md) |
| Consumer group create/show/list/delete | `az eventhubs eventhub consumer-group` | [integration.md](references/integration.md) |
| Authorization rule & keys | `az eventhubs namespace authorization-rule` / `eventhub authorization-rule` | [integration.md](references/integration.md) |
| Capture configuration | `az eventhubs eventhub update --capture-enabled` | [integration.md](references/integration.md) |
| Metrics and logs | `az monitor metrics list`, Log Analytics | [aiops.md](references/aiops.md) |
| Incident RCA | Evidence → timeline → root-cause rules → risk-ranked actions | [troubleshooting.md](references/troubleshooting.md), [aiops.md](references/aiops.md) |

## Safety Gates

Require explicit human confirmation with exact resource name and Resource Group before:
- delete namespace, delete event hub, or delete consumer group;
- regenerate primary/secondary keys;
- scale down throughput (TU/PU reduction);
- disable Capture, disable auto-inflate, or reduce partition count (not possible after creation);
- any change to production networking/private endpoint configuration.
- enable auto-inflate (confirm budget impact for automatic scaling).

If confirmation is missing or user asks to skip it, HALT and explain the required confirmation.

## AIOps and RCA Rules

Use AIOps only for observation, correlation, diagnosis, and recommendations. Do not auto-remediate. Load [aiops.md](references/aiops.md) when symptoms include throughput throttling, partition skew, consumer lag, Capture failures, connection errors, or unknown incident cause.

RCA output must include: symptom, timeline, evidence, likely root causes, confidence, safe checks, risky actions needing approval, and escalation criteria.

## Recovery Matrix

| Condition | Agent Action |
|-----------|--------------|
| AuthorizationFailed / AccessDenied | HALT; report required RBAC from [integration.md](references/integration.md) |
| ResourceNotFound | HALT; verify name, Resource Group, subscription |
| InvalidLocation / SKU unavailable | HALT; validate Location/SKU and suggest supported options |
| Quota/capacity exhausted | HALT; request quota increase or choose another Location/SKU |
| Throttling / 429 | Backoff and retry up to 3x |
| 5xx / transient network | Retry up to 3x, then HALT with correlation ID |
| Destructive action without confirmation | HALT; require explicit confirmation |

## Quality Gate

GCL is required for destructive/disruptive operations and recommended for incident RCA. Use [rubric.md](references/rubric.md) and [prompt-templates.md](references/prompt-templates.md). Rubric dimensions: correctness, safety, idempotency, traceability, spec compliance, RCA quality. Safety score `0` aborts immediately. max_iterations: 2 for destructive/disruptive operations.

Persist GCL traces to `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` with secrets masked as `***`.
## L4 Auto-Feedback Loop

For autonomous operation on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-eventhub-ops \
  --operation namespace_create \
  --command "az eventhubs namespace create --name {{user.namespace_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"provisioningState": "Succeeded"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (namespace_create): auto-feedback loop active
- **Risky operations** (delete): always bypass loop and require explicit human confirmation
- Healing policy: see [`scripts/self_healing/eventhub_heal.json`](../../scripts/self_healing/eventhub_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Integration and Commands](references/integration.md)
- [Troubleshooting and RCA](references/troubleshooting.md)
- [AIOps Analysis](references/aiops.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)


> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
