---
name: azure-postgres-ops
description: >-
  Use when operating or diagnosing Azure Database for PostgreSQL Flexible Server.
  User mentions PostgreSQL, Postgres, Flexible Server, database connections,
  slow queries, storage pressure, failover, backup/restore, firewall, private
  access, or PostgreSQL AIOps/RCA.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials,
  network access to Azure management endpoints and database endpoints.
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

# Azure PostgreSQL Operations Skill

## Overview

Azure Database for PostgreSQL Flexible Server provides managed PostgreSQL with compute, storage, backup, HA, and networking controls. This skill handles server operations, safe diagnostics, AIOps-assisted incident analysis, and root-cause investigation. Keep this file concise; load references for commands, SDK patterns, RCA rules, and detailed scenarios.

## Trigger & Scope

### SHOULD Use When
- User mentions Azure PostgreSQL, Postgres, Flexible Server, database restart/stop/start, firewall, private access, backup, restore, slow query, connection failure, high CPU/IO/storage, lock, deadlock, or RCA.
- Task involves PostgreSQL Flexible Server create/show/list/update/delete, start/stop/restart, scale, firewall rules, backup/restore, metrics/logs, or incident analysis.
- User asks for AIOps analysis, anomaly detection, incident timeline, root cause, query-performance triage, or remediation plan for PostgreSQL symptoms.

### SHOULD NOT Use When
- Billing/cost only → delegate to `azure-cost-ops`.
- Cross-product audit, RBAC, locks, policy, or Activity Log-only analysis → delegate to `azure-audit-ops`.
- Generic metrics/log query authoring → delegate to `azure-monitor-ops`.
- Deep VNet/Private DNS design not specific to PostgreSQL → provide entry diagnostics, then escalate to network owner.
- Application SQL rewrite or DDL execution → provide evidence and DBA-reviewed suggestions only.

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; required for server operations |
| `{{user.location}}` | User input | Azure Location, e.g. `eastus`; validate before create |
| `{{user.server_name}}` | User input | PostgreSQL Flexible Server name |
| `{{user.database_name}}` | User input | Database name for diagnostics only |
| `{{user.sku_name}}` | User input | Compute SKU, e.g. `Standard_D4s_v3` |
| `{{user.analysis_window}}` | User input | Default `PT1H`; use `PT6H`/`P1D` for incidents |
| `{{output.server_id}}` | CLI/SDK output | Parse from `.id` |
| `{{output.metric_window}}` | Monitor output | Parsed anomaly window |

## JSON Paths

```yaml
SERVER_ID: id
SERVER_STATE: state
SERVER_VERSION: version
SERVER_FQDN: fullyQualifiedDomainName
SERVER_SKU: sku.name
STORAGE_MB: storage.storageSizeGb
HA_STATE: highAvailability.state
METRIC_VALUE: value[].timeseries[].data[]
```

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover → Report**.

| Phase | Required Actions |
|-------|------------------|
| Pre-flight | Verify CLI, credentials, subscription, Resource Group, Location, provider, RBAC, target state, and backup/network constraints. |
| Execute | Use Azure CLI primary. Retry transient CLI failures up to 3x with backoff before SDK fallback. |
| Validate | Confirm server state/config with `--output json`; poll LRO every 30s, max 45m unless reference says otherwise. |
| Recover | Apply HALT-vs-retry matrix; never guess fields or execute DDL automatically. |
| Report | Return evidence, confidence, safe next actions, DBA review items, and actions requiring confirmation. |

## Operation Map

| Intent | Primary CLI | Reference |
|--------|-------------|-----------|
| Create/show/list/update/delete | `az postgres flexible-server` | [integration.md](references/integration.md) |
| Start/stop/restart/scale | `az postgres flexible-server start/stop/restart/update` | [integration.md](references/integration.md) |
| Firewall/network/private access | `az postgres flexible-server firewall-rule`, networking commands | [troubleshooting.md](references/troubleshooting.md) |
| Backup/restore/PITR | `az postgres flexible-server restore` | [integration.md](references/integration.md) |
| Metrics/logs/query triage | `az monitor metrics list`, diagnostic logs, Query Store | [aiops.md](references/aiops.md) |
| Incident RCA | Evidence → timeline → root-cause rules → risk-ranked actions | [troubleshooting.md](references/troubleshooting.md), [aiops.md](references/aiops.md) |

## Safety Gates

Require explicit human confirmation with exact server name and Resource Group before:
- delete server, stop production server, restart, restore into/over a critical target, or failover-like disruptive action;
- scale down compute/storage-related changes with performance risk;
- open firewall broadly or change private networking for production;
- run DDL, create/drop index, kill sessions, or change server parameters.

This skill may recommend SQL/DDL for DBA review but must not execute it automatically.

## AIOps and RCA Rules

Use AIOps only for observation, correlation, diagnosis, and recommendations. Do not auto-remediate. Load [aiops.md](references/aiops.md) when symptoms include CPU, memory, IOPS, storage, connection failures, deadlocks, slow queries, WAL growth, lock contention, replication lag, or unknown incident cause.

RCA output must include: incident summary, timeline, metric anomalies, query/log evidence, likely root causes, confidence, safe checks, risky remediation needing approval, DBA review items, and escalation criteria.

## Recovery Matrix

| Condition | Agent Action |
|-----------|--------------|
| AuthorizationFailed / AccessDenied | HALT; report required RBAC from [integration.md](references/integration.md) |
| ResourceNotFound | HALT; verify name, Resource Group, subscription |
| InvalidLocation / SKU unavailable | HALT; validate Location/SKU and suggest supported options |
| Quota/capacity exhausted | HALT; request quota/capacity or choose another Location/SKU |
| Throttling / 429 | Backoff and retry up to 3x |
| 5xx / transient network | Retry up to 3x, then HALT with correlation ID |
| Destructive/disruptive action without confirmation | HALT; require explicit confirmation |
| Evidence suggests DDL | HALT before execution; produce DBA review recommendation |

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

