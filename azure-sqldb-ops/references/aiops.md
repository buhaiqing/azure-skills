# Azure SQL Database AIOps Analysis

## Purpose

AIOps in this skill means metric anomaly detection, evidence correlation, query/log signal ranking, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Inputs

| Input | Source |
|-------|--------|
| Server/DB state/config | `az sql server show`, `az sql db show` |
| Metrics | Azure Monitor metrics (server-scoped and DB-scoped) |
| Activity timeline | Activity Log, delegate deep audit to `azure-audit-ops` |
| Diagnostic logs | Log Analytics if enabled; delegate complex KQL to `azure-monitor-ops` |
| Query evidence | Query Store, `sys.dm_exec_query_stats`, DBA-provided output |
| User incident context | symptom, start time, impacted clients, recent deploys |

## Analysis Windows

| Window | Use |
|--------|-----|
| `PT1H` | Active incident, high-resolution triage |
| `PT6H` | Incident evolution and recent changes |
| `P1D` | Capacity/storage trend and daily pattern |
| Baseline same hour previous day/week | Avoid false positives from normal traffic cycles |

## Metric Collection

```bash
az monitor metrics list \
  --resource "{{output.server_id}}" \
  --metric "dtu_consumption_percent,cpu_percent,storage_percent,storage,sessions_percent,workers_percent,connection_failed,deadlock" \
  --interval PT1M \
  --aggregation Average,Maximum,Total \
  --start-time "{{user.start_time}}" \
  --end-time "{{user.end_time}}" \
  --output json
```

For a specific database, target `{{output.database_id}}` with DB-scoped metrics (e.g. `dtu_consumption_percent`, `cpu_percent`, `storage_percent`). If exact metrics differ, query definitions first and map equivalent metrics.

## Anomaly Rules

| Signal | Detection Rule | Root-Cause Candidates |
|--------|----------------|-----------------------|
| DTU high | sustained > 80% or > 2x baseline | slow query, missing index, plan change, traffic surge |
| CPU high (vCore) | sustained > 80% or sharp rise | sort/hash spill, workload surge, SKU limit |
| Storage high | > 85% or fast growth trend | data load, log pressure, index bloat, long transactions |
| Sessions/workers high | > 80% of limit or > 2x baseline | pool leak, pool sizing, long sessions |
| Failed connections | > baseline by 2x or sustained nonzero | firewall, DNS, auth, secret rotation |
| Deadlocks | nonzero or above baseline | transaction ordering, lock contention |
| Throttling signals (`10928`/`10929`) | DTU pegged + error codes | workload surge, pool undersized |

## Correlation Rules

### Change Correlation

If anomaly start is within 30 minutes after Activity Log or deployment event, increase confidence for that event as a cause.

High-risk change categories:
- server start/stop;
- scale/update (service objective, Max Size);
- firewall/private-access change;
- server parameter update;
- application deployment reported by user.

### Query Correlation

If DTU/CPU rises and Query Store or `sys.dm_exec_query_stats` shows a query with high total time, rows scanned, temp usage, or call volume, classify query workload as a candidate. DDL/index recommendations require DBA review.

### Connection Correlation

If failed connections rise while CPU/IO remain normal, prioritize firewall, DNS/private access, auth, TLS, or client pool configuration over compute scaling.

### Storage Correlation

If storage grows quickly while user reports no data growth, prioritize transaction-log pressure, tempdb spill, index/heap bloat, long transactions, and autovacuum-equivalent lag (for migrated workloads).

## Confidence Scoring

| Level | Requirement |
|-------|-------------|
| High | Metrics, logs/query evidence, and timeline agree |
| Medium | Metrics match symptom and timeline, but query/log evidence is missing |
| Low | Single signal or weak timing; more evidence needed |

Never present low-confidence hypotheses as facts.

## Risk-Ranked Recommendation Model

| Risk | Examples | Agent Behavior |
|------|----------|----------------|
| Safe | read metrics, show config, list firewall rules, query Activity Log | execute directly |
| Low | enable additional diagnostic collection when non-disruptive | ask if cost/noise impact unclear |
| Medium | scale up, narrow firewall change, server start/stop | require confirmation and rollback note |
| High | delete, stop, broad firewall, scale down, T-SQL/DDL, kill sessions, parameter changes | require explicit confirmation; T-SQL/session actions require DBA review |

## DBA Review Items

Use this format for database-level recommendations:

```text
DBA review item: <index/query/parameter/session topic>
Evidence: <metric/log/query signal>
Suggested validation: <Query Store, sys.dm_exec_*, lock view, stats update>
Risk: <blocking, write amplification, table lock, restart needed>
Do not execute automatically: true
```

## AIOps Report Template

```text
Incident: <short title>
Window analyzed: <start/end + baseline>
Anomalies:
- <metric>: <observed> vs <baseline>, time <window>
Correlations:
- <Activity Log/config/app/query event> within <minutes> of anomaly
Root-cause candidates:
1. <candidate> — Confidence: High|Medium|Low — Evidence: <evidence>
2. <candidate> — Confidence: High|Medium|Low — Evidence: <evidence>
Safe checks completed:
- <command/result summary>
Recommended next actions:
- Safe: <diagnostic>
- Approval required: <operation + impact>
DBA review:
- <query/index/parameter/session item>
Escalation:
- <team/support condition>
```

## Guardrails

- Do not claim causality from correlation alone.
- Do not run T-SQL/DDL, kill sessions, start/stop server, delete, or broad firewall changes as part of AIOps.
- Do not request or expose database passwords or connection strings.
- Mask any accidentally returned credential-like value as `***`.
- If evidence is insufficient, state what evidence is missing.
