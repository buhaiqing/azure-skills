---
name: azure-redis-ops
description: >-
  Use when operating or diagnosing Azure Cache for Redis or Azure Managed Redis
  resources. User mentions Redis, Azure Cache for Redis, cache latency, eviction,
  memory pressure, hit rate, key rotation, Redis networking, or Redis AIOps/RCA.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials,
  network access to Azure management endpoints and Redis endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-06-09"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Redis Operations Skill

## Overview

Azure Cache for Redis provides managed in-memory caching. This skill handles Redis instance operations, safe diagnostics, AIOps-assisted incident analysis, and root-cause investigation. Keep this file concise; load reference files for commands, SDK patterns, RCA rules, and detailed scenarios.

## Trigger & Scope

### SHOULD Use When
- User mentions Azure Cache for Redis, Azure Managed Redis, Redis Enterprise, cache latency, eviction, memory, hit rate, key rotation, reboot, or Redis private endpoint.
- Task involves Redis instance create/show/list/update/delete, scale, reboot, access keys, firewall/network checks, metrics, logs, or incident RCA.
- User asks for AIOps analysis, anomaly detection, incident timeline, root cause, or remediation plan for Redis symptoms.

### SHOULD NOT Use When
- Billing/cost only → delegate to `azure-cost-ops`.
- Cross-product audit, RBAC, locks, policy, or Activity Log-only analysis → delegate to `azure-audit-ops`.
- Generic metrics/log query authoring → delegate to `azure-monitor-ops`.
- VNet, DNS, or Private Link deep dive not specific to Redis → provide entry diagnostics, then escalate to network owner.
- Application code cache pattern redesign → provide findings only; app owners must change code.

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; required for resource operations |
| `{{user.location}}` | User input | Azure Location, e.g. `eastus`; validate before create |
| `{{user.redis_name}}` | User input | Redis resource name; ask once |
| `{{user.sku}}` | User input | Basic, Standard, Premium, Enterprise family |
| `{{user.capacity}}` | User input | Redis cache size/capacity |
| `{{user.analysis_window}}` | User input | Default `PT1H`; use `PT6H`/`P1D` for incidents |
| `{{output.redis_id}}` | CLI/SDK output | Parse from `.id` |
| `{{output.metric_window}}` | Monitor output | Parsed anomaly window |

## JSON Paths

```yaml
REDIS_ID: id
REDIS_HOST: hostName
REDIS_SSL_PORT: sslPort
REDIS_PROVISIONING_STATE: provisioningState
REDIS_PRIVATE_ENDPOINTS: privateEndpointConnections[].privateEndpoint.id
METRIC_VALUE: value[].timeseries[].data[]
```

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover → Report**.

| Phase | Required Actions |
|-------|------------------|
| Pre-flight | Verify CLI, credentials, subscription, Resource Group, Location, provider, RBAC, and target resource state. |
| Execute | Use Azure CLI primary. Retry transient CLI failures up to 3x with backoff before SDK fallback. |
| Validate | Confirm provisioning/state/metric result with `--output json`; poll LRO every 30s, max 30m unless reference says otherwise. |
| Recover | Apply HALT-vs-retry matrix; never guess fields or retry destructive actions blindly. |
| Report | Return evidence, confidence, safe next actions, and actions requiring confirmation. |

## Operation Map

| Intent | Primary CLI | Reference |
|--------|-------------|-----------|
| Create/show/list/update/delete | `az redis` / `az redisenterprise` | [integration.md](references/integration.md) |
| Scale, reboot, key rotation | `az redis update`, `az redis force-reboot`, `az redis regenerate-keys` | [integration.md](references/integration.md) |
| Network/firewall/private endpoint | `az redis firewall-rules`, `az network private-endpoint-connection` | [troubleshooting.md](references/troubleshooting.md) |
| Metrics and logs | `az monitor metrics list`, Log Analytics | [aiops.md](references/aiops.md) |
| Incident RCA | Evidence → timeline → root-cause rules → risk-ranked actions | [troubleshooting.md](references/troubleshooting.md), [aiops.md](references/aiops.md) |

## Safety Gates

Require explicit human confirmation with exact Redis name and Resource Group before:
- delete Redis resource, purge data, or flush cache data;
- force reboot or shard reboot;
- regenerate primary/secondary keys;
- scale down, disable TLS, enable non-SSL port, or widen firewall access;
- any change to production networking/private endpoint configuration.

If confirmation is missing or user asks to skip it, HALT and explain the required confirmation.

## AIOps and RCA Rules

Use AIOps only for observation, correlation, diagnosis, and recommendations. Do not auto-remediate. Load [aiops.md](references/aiops.md) when symptoms include latency, timeouts, memory pressure, evictions, hit-rate drops, connection spikes, bandwidth saturation, or unknown incident cause.

RCA output must include: symptom, timeline, evidence, likely root causes, confidence, safe checks, risky actions needing approval, and escalation criteria.

## Recovery Matrix

| Condition | Agent Action |
|-----------|--------------|
| AuthorizationFailed / AccessDenied | HALT; report required RBAC from [integration.md](references/integration.md) |
| ResourceNotFound | HALT; verify name, Resource Group, subscription |
| InvalidLocation / SKU unavailable | HALT; validate Location/SKU and suggest supported options |
| Quota/capacity exhausted | HALT; request quota/capacity or choose another Location/SKU |
| Throttling / 429 | Backoff and retry up to 3x |
| 5xx / transient network | Retry up to 3x, then HALT with correlation ID |
| Destructive action without confirmation | HALT; require explicit confirmation |

## Quality Gate

GCL is required for destructive/disruptive operations and recommended for incident RCA. Use [rubric.md](references/rubric.md) and [prompt-templates.md](references/prompt-templates.md). Rubric dimensions: correctness, safety, idempotency, traceability, spec compliance, RCA quality. Safety score `0` aborts immediately.

Persist GCL traces to `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` with secrets masked as `***`.

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Integration and Commands](references/integration.md)
- [Troubleshooting and RCA](references/troubleshooting.md)
- [AIOps Analysis](references/aiops.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)
