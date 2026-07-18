---
name: azure-servicebus-ops
description: >-
  Use when operating Azure Service Bus resources (namespaces, queues, topics,
  subscriptions, rules) via Azure CLI or Azure SDK. User mentions Service Bus,
  queue, topic, subscription, dead-letter, message TTL, or Service Bus AIOps/RCA.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials,
  network access to Azure Service Bus management endpoints.
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

# Azure Service Bus Operations Skill

## Overview

Azure Service Bus provides managed message brokering with queues (point-to-point), topics/subscriptions (pub-sub), and dead-letter queues. This skill handles namespace/resource operations, safe diagnostics, and AIOps-assisted incident analysis. Keep this file concise; load reference files for commands, SDK patterns, RCA rules, and detailed scenarios.

## Trigger & Scope

### SHOULD Use When
- User mentions Azure Service Bus, queue, topic, subscription, dead-letter, message TTL/duplication detection/partitioning.
- Task involves CRUD on namespace, queue, topic, subscription, rule; show/list/authorization-rule operations; AIOps for dead-letter buildup, quota exhaustion, message delay, or connectivity.
- Keywords: servicebus, sb, deadletter, dlq, ttl, messagelock.

### SHOULD NOT Use When
- Billing/cost only → delegate to `azure-cost-ops`.
- Generic metrics/log query authoring → delegate to `azure-monitor-ops`.
- Logic Apps, Event Grid, Event Hubs message routing → delegate to respective skill (TBD).
- Cross-product audit, RBAC, locks, policy-only work → delegate to `azure-audit-ops`.
- Application code message-processing pattern redesign → provide findings only; app owners must change code.

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; required for all resource operations |
| `{{user.location}}` | User input | Azure Location, e.g. `eastus`; validate before create |
| `{{user.namespace_name}}` | User input | Service Bus namespace name; globally unique |
| `{{user.queue_name}}` | User input | Queue name within namespace |
| `{{user.topic_name}}` | User input | Topic name within namespace |
| `{{user.subscription_name}}` | User input | Subscription name under topic |
| `{{output.namespace_id}}` | CLI/SDK output | Parse from `.id` |
| `{{output.analysis_window}}` | Monitor output | Parsed anomaly window |

## JSON Paths

```yaml
NAMESPACE_ID: id
NAMESPACE_PROVISIONING_STATE: provisioningState
QUEUE_NAME: name
QUEUE_COUNT: countDetails.activeMessageCount
TOPIC_NAME: name
SUBSCRIPTION_NAME: name
DLQ_COUNT: countDetails.deadLetterMessageCount
METRIC_VALUE: value[].timeseries[].data[]
```

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover → Report**.

| Phase | Required Actions |
|-------|------------------|
| Pre-flight | Verify CLI, credentials, subscription, Resource Group, Location, provider (`Microsoft.ServiceBus`), RBAC, and target resource state. |
| Execute | Use Azure CLI primary. Retry transient CLI failures up to 3x with backoff before SDK fallback. |
| Validate | Confirm provisioning state with `--output json`; poll LRO every 30s, max 30m. |
| Recover | Apply HALT-vs-retry matrix; never guess fields or retry destructive actions blindly. |
| Report | Return evidence, confidence, safe next actions, and actions requiring confirmation. |

## Operation Map

| Intent | Primary CLI | Reference |
|--------|-------------|-----------|
| Create namespace/queue/topic/subscription/rule | `az servicebus namespace create` / `az servicebus queue create` / `az servicebus topic create` / `az servicebus topic subscription create` / `az servicebus topic subscription rule create` | [integration.md](references/integration.md) |
| Show/list | `az servicebus * show` / `az servicebus * list` | [integration.md](references/integration.md) |
| Authorization rules and keys | `az servicebus namespace authorization-rule` / `az servicebus queue authorization-rule` / `az servicebus topic authorization-rule` | [integration.md](references/integration.md) |
| Delete | `az servicebus * delete` | [integration.md](references/integration.md) |
| Metrics and diagnostics | `az monitor metrics list`, `az monitor activity-log list` | [troubleshooting.md](references/troubleshooting.md) |
| Incident RCA | Evidence → timeline → root-cause rules → risk-ranked actions | [troubleshooting.md](references/troubleshooting.md), [aiops.md](references/aiops.md) |

## Safety Gates

Require explicit human confirmation with exact resource name and Resource Group before:
- delete namespace, queue, topic, subscription;
- regenerate primary/secondary keys;
- any change to production networking/private endpoint configuration.

If confirmation is missing or user asks to skip it, HALT and explain the required confirmation.

## AIOps and RCA Rules

Use AIOps only for observation, correlation, diagnosis, and recommendations. Do not auto-remediate. Load [aiops.md](references/aiops.md) when symptoms include dead-letter buildup, quota exhaustion, message delay, connectivity issues, or unknown incident cause.

RCA output must include: symptom, timeline, evidence, likely root causes, confidence, safe checks, risky actions needing approval, and escalation criteria.

## Recovery Matrix

| Condition | Agent Action |
|-----------|--------------|
| AuthorizationFailed / AccessDenied | HALT; report required RBAC from [integration.md](references/integration.md) |
| ResourceNotFound | HALT; verify name, Resource Group, subscription |
| InvalidLocation / SKU unavailable | HALT; validate Location/SKU and suggest supported options |
| Quota/capacity exhausted | HALT; request quota increase or choose another tier |
| Throttling / 429 | Backoff and retry up to 3x |
| 5xx / transient network | Retry up to 3x, then HALT with correlation ID |
| Destructive action without confirmation | HALT; require explicit confirmation |

## Quality Gate

GCL is required for destructive operations and recommended for incident RCA. Use [rubric.md](references/rubric.md) and [prompt-templates.md](references/prompt-templates.md). Rubric dimensions: correctness, safety, idempotency, traceability, spec compliance, RCA quality. Safety score `0` aborts immediately.

Persist GCL traces to `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` with secrets masked as `***`.

## L4 Auto-Feedback Loop

For autonomous operation on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-servicebus-ops \
  --operation namespace_create \
  --command "az servicebus namespace create --name {{user.namespace_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"provisioningState": "Succeeded"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (namespace_create): auto-feedback loop active
- **Risky operations** (delete): always bypass loop and require explicit human confirmation
- Healing policy: see [`scripts/self_healing/servicebus_heal.json`](../../scripts/self_healing/servicebus_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Integration and Commands](references/integration.md)
- [Troubleshooting and RCA](references/troubleshooting.md)
- [AIOps Analysis](references/aiops.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

