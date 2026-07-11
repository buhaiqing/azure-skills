---
name: azure-cosmos-ops
description: >-
  Use when operating or diagnosing Azure Cosmos DB accounts, databases,
  containers, throughput (RU/s), partition keys, global distribution, or
  Cosmos DB AIOps/RCA (throttling, 429, hot partition, RU/s tuning).
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials,
  network access to Azure management endpoints and Cosmos DB data endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-07-12"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Cosmos DB Operations Skill

## Overview

Azure Cosmos DB is a globally distributed, multi-model database service. This skill handles account/database/container CRUD, throughput (RU/s) management, global distribution, key diagnostics, and AIOps-assisted incident analysis (throttling, hot partition, RU/s tuning). Keep this file concise; load references for commands, SDK patterns, RCA rules, and detailed scenarios.

## Trigger & Scope

### SHOULD Use When
- User mentions Azure Cosmos DB, Cosmos account, SQL/Mongo/Cassandra/Gremlin/Table API, RU/s, request units, throughput, partition key, 429 throttling, hot partition, or global distribution / multi-region writes.
- Task involves Cosmos account create/show/list/update/delete, database/container create/show/delete, RU/s scale (manual/autoscale), key list/regenerate, consistency level, or region add/failover.
- User asks for AIOps analysis, throttling RCA, partition skew diagnosis, normalized RU, or throughput tuning recommendations.

### SHOULD NOT Use When
- Billing/cost only → delegate to `azure-cost-ops`.
- Cross-product audit, RBAC, locks, policy, or Activity Log-only analysis → delegate to `azure-audit-ops`.
- Private endpoint / private DNS design → delegate to `azure-privateendpoint-ops` (this skill may show network info, then hand off).
- Generic metrics/alert KQL authoring → delegate to `azure-monitor-ops`.
- Application data-plane query rewrite (SQL/Mongo statements) → provide evidence and DBA/app-reviewed suggestions only; do not execute arbitrary DML automatically.

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; required for all resource operations |
| `{{user.location}}` | User input | Azure Location, e.g. `eastus`; validate before create |
| `{{user.account_name}}` | User input | Cosmos DB account name (globally unique DNS label) |
| `{{user.api_kind}}` | User input | `sql`/`mongodb`/`cassandra`/`gremlin`/`table` |
| `{{user.database_name}}` | User input | Database name |
| `{{user.container_name}}` | User input | Container/collection/table name |
| `{{user.partition_key}}` | User input | Partition key path, e.g. `/tenantId` |
| `{{user.throughput_rus}}` | User input | Manual RU/s (e.g. `400`); min depends on API |
| `{{user.max_throughput_rus}}` | User input | Autoscale max RU/s |
| `{{user.analysis_window}}` | User input | Default `PT1H`; use `PT6H`/`P1D` for incidents |
| `{{user.consistency_level}}` | User input | Ask once; e.g. `Session`, `BoundedStaleness`, `Strong` |
| `{{user.baseline_window}}` | User input | Ask once; baseline comparison window, e.g. previous day same hour |
| `{{user.start_time}}` | User input | Ask once; ISO 8601 start time for metrics queries |
| `{{user.end_time}}` | User input | Ask once; ISO 8601 end time for metrics queries |
| `{{output.account_id}}` | CLI/SDK output | Parse from `.id` |
| `{{output.container_id}}` | CLI/SDK output | Parse from `.id` |

## JSON Paths

```yaml
ACCOUNT_ID: id; ACCOUNT_STATE: provisioningState; ACCOUNT_KIND: kind
CONSISTENCY: consistencyPolicy.defaultConsistencyLevel
LOCATIONS: locations[].locationName; DB_ID: id; CONTAINER_ID: id
THROUGHPUT: resource.throughput; MAX_THROUGHPUT: resource.maxThroughput
```

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover → Report**.

| Phase | Required Actions |
|-------|------------------|
| Pre-flight | Verify CLI, credentials, subscription, Resource Group, Location, provider, RBAC, target state, and throughput/consistency constraints. |
| Execute | Use Azure CLI primary. Retry transient CLI failures up to 3x with backoff before SDK fallback. |
| Validate | Confirm account/container state/config with `--output json`; poll LRO every 30s, max 45m unless reference says otherwise. |
| Recover | Apply HALT-vs-retry matrix; never guess fields; do not auto-tune RU/s to unsafe values. |
| Report | Return evidence, confidence, safe next actions, approval items, and actions requiring confirmation. |

## Operation Map

| Intent | Primary CLI | Reference |
|--------|-------------|-----------|
| Create/show/list/update/delete account | `az cosmosdb` | [integration.md](references/integration.md) |
| SQL database/container CRUD | `az cosmosdb sql database`, `az cosmosdb sql container` | [integration.md](references/integration.md) |
| RU/s manual / autoscale | `az cosmosdb sql container throughput update` | [integration.md](references/integration.md) |
| List/regenerate keys, connection strings | `az cosmosdb keys`, `az cosmosdb list-connection-strings` | [integration.md](references/integration.md) |
| Consistency / global distribution / failover | `az cosmosdb update`, `az cosmosdb region` | [integration.md](references/integration.md) |
| Throttling / hot partition / RU/s RCA | metrics, diagnostics | [aiops.md](references/aiops.md) |
| Incident RCA | Evidence → timeline → root-cause rules → risk-ranked actions | [troubleshooting.md](references/troubleshooting.md), [aiops.md](references/aiops.md) |

> Mongo/Cassandra/Gremlin/Table API share the same account-level commands; only the database/container CRUD subcommands differ (`az cosmosdb mongodb ...`, `az cosmosdb cassandra ...`, etc.). This skill documents the SQL API path in detail; mirror it for other APIs.

## Safety Gates

Require explicit human confirmation with exact account name and Resource Group before:
- delete account or container (irreversible data loss);
- regenerate keys (breaks live connections);
- change default consistency level or enable/disable multi-region writes in production;
- add/remove regions with failover/replication impact;
- scale down RU/s below current steady-state or disable autoscale on a hot workload.

This skill may recommend RU/s / partition changes for review but must not auto-apply unsafe throughput reductions.

## AIOps and RCA Rules

Use AIOps only for observation, correlation, diagnosis, and recommendations. Do not auto-remediate. Load [aiops.md](references/aiops.md) when symptoms include 429 throttling, total/high RU consumption, normalized RU spikes, partition key skew, replication conflict, or unknown incident cause.

RCA output must include: incident summary, timeline, metric anomalies, log/diagnostic evidence, likely root causes, confidence, safe checks, risky remediation needing approval, and escalation criteria.

## Recovery Matrix

| Condition | Agent Action |
|-----------|--------------|
| AuthorizationFailed / AccessDenied | HALT; report required RBAC from [integration.md](references/integration.md) |
| ResourceNotFound | HALT; verify name, Resource Group, subscription |
| InvalidLocation / API unsupported | HALT; validate Location/API and suggest supported options |
| Quota/capacity exhausted | HALT; request quota increase or choose another Location |
| Throttling / 429 (RU/s) | Backoff and retry up to 3x; recommend RU/s increase only after evidence |
| 5xx / transient network | Retry up to 3x, then HALT with correlation ID |
| Destructive/disruptive action without confirmation | HALT; require explicit confirmation |
| Evidence suggests unsafe RU/s reduction | HALT before applying; produce review recommendation |

## Quality Gate

GCL is required for destructive/disruptive operations (delete, key regenerate, consistency/failover, region change, scale down) and recommended for incident RCA. Use [rubric.md](references/rubric.md) and [prompt-templates.md](references/prompt-templates.md). Rubric dimensions: correctness, safety, idempotency, traceability, spec compliance, RCA quality. Safety score `0` aborts immediately.

`{{output.rubric}}`、`{{output.critic_feedback}}`、`{{output.generator_output}}`、`{{output.trace}}` 为 GCL 运行时占位符，由编排器填充。

Persist GCL traces to `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` with secrets masked as `***`.

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Integration and Commands](references/integration.md)
- [Troubleshooting and RCA](references/troubleshooting.md)
- [AIOps Analysis](references/aiops.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)
