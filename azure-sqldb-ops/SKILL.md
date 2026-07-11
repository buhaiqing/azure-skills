---
name: azure-sqldb-ops
description: >-
  Use when operating or diagnosing Azure SQL Database (logical server, single
  database, elastic pool, or managed instance). User mentions Azure SQL, SQL
  Database, logical server, elastic pool, DTU, vCore, T-SQL, connection
  failures (18456/40814/timeout), deadlocks, slow queries, scaling, firewall,
  or SQL AIOps/RCA.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials,
  network access to Azure management endpoints and database endpoints.
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

# Azure SQL Database Operations Skill
## Overview

Azure SQL Database is a managed PaaS relational engine. Covers logical server, single database, elastic pool, and (read-only diagnostics for) managed instance: provisioning, safe scaling, firewall/networking, connection diagnostics, AIOps-assisted incident analysis, and RCA. Load references for commands, SDK patterns, and detailed scenarios.

## Trigger & Scope

### SHOULD Use When
- User mentions Azure SQL Database, SQL DB, logical server, elastic pool, managed instance, DTU, vCore, T-SQL, or Transact-SQL.
- Task involves create/show/list/update/delete of server, database, or elastic pool; start/stop; scale (compute/Max Size); firewall rules; metrics/logs; or incident analysis.
- User reports connection failure (18456/40814/timeout), high DTU/CPU, blocking/deadlocks, slow queries, or storage/transaction log pressure.
- User asks for AIOps analysis, anomaly detection, incident timeline, root cause, query-performance triage, or remediation plan.

### SHOULD NOT Use When
- Billing/cost only → delegate to `azure-cost-ops`.
- Cross-product audit, RBAC, locks, policy, or Activity Log-only → delegate to `azure-audit-ops`.
- Generic metrics/log query authoring (KQL) → delegate to `azure-monitor-ops`.
- Deep VNet/Private DNS design not specific to SQL DB → entry diagnostics, then escalate.
- Data-factory/Synapse/pipeline → delegate to data-movement skill; this skill handles only the SQL DB endpoint.
- Application T-SQL rewrite or DDL execution → evidence and DBA-reviewed suggestions only; no auto-execute.

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; required for all operations |
| `{{user.location}}` | User input | Azure Location, e.g. `eastus`; validate before create |
| `{{user.server_name}}` | User input | Logical server name (`<name>.database.windows.net`) |
| `{{user.database_name}}` | User input | Database name |
| `{{user.elastic_pool_name}}` | User input | Elastic pool name for pool-scoped ops |
| `{{user.service_objective}}` | User input | e.g. `S0`, `P1`, `GP_Gen5_4`, `HS_Gen5_8` |
| `{{user.analysis_window}}` | User input | Default `PT1H`; use `PT6H`/`P1D` for incidents |
| `{{user.admin_login}}` | User input | Server admin login (create server) |
| `{{user.vcore_count}}` | User input | vCore capacity for vCore-based create/scale |
| `{{user.max_size}}` | User input | Max size for storage scaling |
| `{{user.pool_edition}}` | User input | Elastic pool edition |
| `{{user.pool_capacity}}` | User input | Elastic pool capacity (DTU or vCores) |
| `{{user.rule_name}}` | User input | Firewall rule name |
| `{{user.start_ip}}` | User input | Firewall rule start IP |
| `{{user.end_ip}}` | User input | Firewall rule end IP |
| `{{user.access_mode}}` | User input | Public/private network access mode |
| `{{user.private_dns_zone}}` | User input | Private DNS zone for private endpoint |
| `{{user.vnet_name}}` | User input | VNet name for private endpoint |
| `{{user.subnet_name}}` | User input | Subnet name for private endpoint |
| `{{user.baseline_window}}` | User input | AIOps baseline comparison window |
| `{{user.start_time}}` | User input | Metrics query start time (ISO8601) |
| `{{user.end_time}}` | User input | Metrics query end time (ISO8601) |
| `{{output.server_id}}` | CLI/SDK output | Parse from `.id` |
| `{{output.database_id}}` | CLI/SDK output | Parse from `.id` |

## JSON Paths

```yaml
SERVER_ID: id
SERVER_STATE: state
SERVER_FQDN: fullyQualifiedDomainName
SERVER_VERSION: version
DATABASE_ID: id
DATABASE_STATE: status
DATABASE_MAXSIZE: maxSizeBytes
DATABASE_SLO: currentServiceObjectiveName
ELASTICPOOL_ID: id
ELASTICPOOL_STATE: state
METRIC_VALUE: value[].timeseries[].data[]
```

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover → Report**.

| Phase | Required Actions |
|-------|------------------|
| Pre-flight | Verify CLI, credentials, subscription, Resource Group, Location, provider (`Microsoft.Sql`), RBAC, target state, and backup/network constraints. |
| Execute | Use Azure CLI primary. Retry transient CLI failures up to 3x with backoff before SDK fallback. |
| Validate | Confirm state/config via `--output json`; poll LRO every 30s, max 45m unless reference says otherwise. |
| Recover | Apply HALT-vs-retry matrix; never guess fields or execute T-SQL/DDL automatically. |
| Report | Return evidence, confidence, safe next actions, DBA review items, and actions requiring confirmation. |

## Operation Map

| Intent | Primary CLI | Reference |
|--------|-------------|-----------|
| Create/show/list/update/delete server | `az sql server` | [integration.md](references/integration.md) |
| Create/show/update/delete database | `az sql db` | [integration.md](references/integration.md) |
| Scale DB (compute / Max Size) | `az sql db update` | [integration.md](references/integration.md) |
| Elastic pool create/scale | `az sql elastic-pool` | [integration.md](references/integration.md) |
| Start/stop server | `az sql server start/stop` | [integration.md](references/integration.md) |
| Firewall/network rules | `az sql server firewall-rule`, networking commands | [troubleshooting.md](references/troubleshooting.md) |
| Metrics/logs/query triage | `az monitor metrics list`, diagnostic logs, Query Store | [aiops.md](references/aiops.md) |
| Incident RCA | Evidence → timeline → root-cause rules → risk-ranked actions | [troubleshooting.md](references/troubleshooting.md), [aiops.md](references/aiops.md) |

## Safety Gates
Require explicit human confirmation with exact server/database name and Resource Group before:
- delete server/database/elastic pool (irreversible data loss); stop/start disruptive actions;
- scale down compute or shrink Max Size with performance/data-loss risk;
- open firewall broadly or change private networking/VNet for production;
- run T-SQL, create/drop index, kill sessions, or change server parameters.
This skill may recommend T-SQL/DDL for DBA review but must not auto-execute.

## AIOps and RCA Rules
Use AIOps only for observation, correlation, diagnosis, and recommendations. Do not auto-remediate. Load [aiops.md](references/aiops.md) when symptoms include DTU/CPU, storage/transaction-log pressure, connection failures, blocking/deadlocks, slow queries, lock contention, or unknown incident cause. RCA output must include: incident summary, timeline, metric anomalies, query/log evidence, likely root causes, confidence, safe checks, risky remediation needing approval, DBA review items, and escalation criteria.

## Recovery Matrix
| Condition | Agent Action |
|-----------|--------------|
| AuthorizationFailed / AccessDenied | HALT; report required RBAC per [integration.md](references/integration.md) |
| ResourceNotFound | HALT; verify name, Resource Group, subscription |
| InvalidLocation / SKU unavailable | HALT; validate Location/service objective, suggest supported options |
| Quota/capacity exhausted | HALT; request quota/capacity or choose another Location/objective |
| Throttling / 429 | Backoff and retry up to 3x |
| 5xx / transient network | Retry up to 3x, then HALT with correlation ID |
| Destructive/disruptive action without confirmation | HALT; require explicit confirmation |
| Evidence suggests T-SQL/DDL | HALT before execution; produce DBA review recommendation |

## Quality Gate
GCL is required for destructive/disruptive operations and recommended for incident RCA. Use [rubric.md](references/rubric.md) and [prompt-templates.md](references/prompt-templates.md). Rubric dimensions: correctness, safety, idempotency, traceability, spec compliance, RCA quality. Safety score `0` aborts immediately. Persist GCL traces to `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` with secrets masked as `***`.

## Reference Files
- [Core Concepts](references/core-concepts.md) · [Integration](references/integration.md) · [Troubleshooting](references/troubleshooting.md) · [AIOps](references/aiops.md) · [Rubric](references/rubric.md) · [Prompt Templates](references/prompt-templates.md)
