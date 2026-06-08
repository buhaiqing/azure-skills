# Azure PostgreSQL AIOps Analysis

## Purpose

AIOps in this skill means metric anomaly detection, evidence correlation, query/log signal ranking, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Inputs

| Input | Source |
|-------|--------|
| Server state/config | `az postgres flexible-server show` |
| Metrics | Azure Monitor metrics |
| Activity timeline | Activity Log, delegate deep audit to `azure-audit-ops` |
| Diagnostic logs | Log Analytics if enabled; delegate complex KQL to `azure-monitor-ops` |
| Query evidence | Query Store, `pg_stat_statements`, slow query logs, DBA-provided output |
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
  --metric "cpu_percent,memory_percent,storage_percent,active_connections,connections_failed,iops,deadlocks" \
  --interval PT1M \
  --aggregation Average,Maximum,Total \
  --start-time "{{user.start_time}}" \
  --end-time "{{user.end_time}}" \
  --output json
```

If exact metrics differ, query definitions first and map equivalent metrics.

## Anomaly Rules

| Signal | Detection Rule | Root-Cause Candidates |
|--------|----------------|-----------------------|
| CPU high | sustained > 80% or > 2x baseline | slow query, missing index, plan change, traffic surge |
| Memory high | sustained > 80% or sharp rise | sort/hash spill, workload surge, SKU limit |
| Storage high | > 85% or fast growth trend | WAL/temp growth, bloat, data load, autovacuum lag |
| Connections high | > 80% of configured max or > 2x baseline | pool leak, pool sizing, long sessions |
| Failed connections | > baseline by 2x or sustained nonzero | firewall, DNS, auth, secret rotation |
| IOPS high | > 2x baseline with query latency | scan-heavy workload, bloat, checkpoint pressure |
| Deadlocks | nonzero or above baseline | transaction ordering, lock contention |
| Replication lag | rising lag where replicas exist | replica pressure, network/storage bottleneck |

## Correlation Rules

### Change Correlation

If anomaly start is within 30 minutes after Activity Log or deployment event, increase confidence for that event as a cause.

High-risk change categories:
- restart/stop/start;
- scale/update;
- firewall/private access change;
- server parameter update;
- restore/cutover;
- application deployment reported by user.

### Query Correlation

If CPU/IOPS rises and Query Store or `pg_stat_statements` shows a query with high total time, rows scanned, temp usage, or call volume, classify query workload as a candidate. DDL/index recommendations require DBA review.

### Connection Correlation

If failed connections rise while CPU/IO remain normal, prioritize firewall, DNS/private access, auth, TLS, or client pool configuration over compute scaling.

### Storage Correlation

If storage grows quickly while user reports no data growth, prioritize WAL retention, temp files, table/index bloat, long transactions, and autovacuum lag.

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
| Medium | scale up, narrow firewall change, restart candidate | require confirmation and rollback note |
| High | delete, stop, broad firewall, restore cutover, DDL, kill sessions, parameter changes requiring restart | require explicit confirmation; DDL/session actions require DBA review |

## DBA Review Items

Use this format for database-level recommendations:

```text
DBA review item: <index/query/parameter/session topic>
Evidence: <metric/log/query signal>
Suggested validation: <EXPLAIN, pg_stat_statements, lock view, vacuum stats>
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
- Do not run DDL, kill sessions, restart, stop, delete, restore, failover-like operations, or broad firewall changes as part of AIOps.
- Do not request or expose database passwords or connection strings.
- Mask any accidentally returned credential-like value as `***`.
- If evidence is insufficient, state what evidence is missing.
