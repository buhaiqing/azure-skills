# Azure SQL Database AIOps Analysis

## Purpose

AIOps in this skill means metric anomaly detection, evidence correlation, query/log signal ranking, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Detection Signals

| Signal | Source | Threshold | Severity |
|--------|--------|-----------|----------|
| dtu_consumption_high | Azure Monitor metrics - `dtu_consumption_percent` | > 80% sustained 10min or > 2x baseline | High |
| connection_failed_spike | Azure Monitor metrics - `connection_failed` | > 2x baseline or sustained nonzero | Critical |
| storage_pressure | Azure Monitor metrics - `storage_percent` | > 85% or fast growth trend | High |
| deadlock_detected | Azure Monitor metrics - `deadlock` | Nonzero count in PT1H window | Medium |
| cpu_high_vcore | Azure Monitor metrics - `cpu_percent` | > 80% sustained 15min (vCore model) | High |
| geo_replication_lag | Azure Monitor metrics - `replication_lag_seconds` | > 60s for > 10min | Medium |

## Inputs

| Input | Source |
|-------|--------|
| Server/DB state/config | `az sql server show`, `az sql db show` |
| Metrics | Azure Monitor metrics (server-scoped and DB-scoped) |
| Activity timeline | Activity Log, delegate deep audit to `azure-monitor-ops` (see `docs/cross-skill-rca-schema.md`) |
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

## RCA Rules

### Rule 1: Connection Failed Spike
- **Trigger**: `connection_failed_spike` detected
- **Diagnostic Steps**:
  1. Check firewall rules: `az sql server firewall-rule list --resource-group <rg> --server <name>`
  2. Verify authentication: check `sys.dm_audit_actions` for login failures
  3. Check private endpoint: `az network private-endpoint-connection list --resource-group <rg>`
  4. Check DNS resolution: verify private DNS zone configuration
  5. Review recent credential rotation or secret expiry
- **Root Causes**:
  - Firewall rule missing or too restrictive
  - Private endpoint misconfiguration
  - Authentication failure (wrong credentials, expired secrets)
  - DNS resolution failure for private endpoint
  - Client IP not in allowed ranges
- **Resolution**: Update firewall rules, fix private endpoint, rotate credentials, or update client connection strings
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的网络层诊断路径

### Rule 2: DTU/CPU High Pressure
- **Trigger**: `dtu_consumption_high` or `cpu_high_vcore` detected
- **Diagnostic Steps**:
  1. Identify top queries: Query Store `sys.query_store_plan` by total time/DTU
  2. Check query plan changes: compare `sys.query_store_plan` historical vs current
  3. Detect missing indexes: `sys.dm_db_missing_index_details`
  4. Check for plan regression: `sys.query_store_plan` with different plan hash
  5. Check workload surge: compare `sessions_percent`, `workers_percent` to baseline
- **Root Causes**:
  - Slow query with missing index
  - Query plan regression after stats update
  - Application workload surge
  - Undersized DTU/vCore tier
  - Parallel query over parallelism threshold
- **Resolution**: Add missing indexes, update statistics, optimize query, or scale up tier
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的性能诊断路径

### Rule 3: Storage Pressure Critical
- **Trigger**: `storage_pressure` detected (> 85% or fast growth)
- **Diagnostic Steps**:
  1. Check database size breakdown: `sp_spaceused`
  2. Identify large tables/indexes: `sys.dm_db_partition_stats`
  3. Check transaction log size: `sys.database_files` where type = 1
  4. Detect long-running transactions: `sys.dm_tran_active_transactions`
  5. Check index fragmentation: `sys.dm_db_index_physical_stats`
- **Root Causes**:
  - Data volume growth (expected)
  - Transaction log not truncating (uncommitted transactions)
  - Index bloat or fragmentation
  - Tempdb spill in memory-optimized queries
  - Backup retention policy consuming space
- **Resolution**: Purge old data, commit/rollback long transactions, rebuild fragmented indexes, increase storage tier
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的存储诊断路径

### Rule 4: Deadlock Detected
- **Trigger**: `deadlock_detected` (nonzero deadlock count)
- **Diagnostic Steps**:
  1. Capture deadlock graph: `sys.event_log` or `sys.dm_xe_sessions` for deadlock_xml
  2. Identify victim and winner processes
  3. Check lock compatibility: review lock modes (X, S, IX, IS)
  4. Analyze transaction isolation level
  5. Review application transaction ordering
- **Root Causes**:
  - Application accessing resources in different order
  - Long-running transactions holding locks
  - Serializable isolation level overused
  - Missing index causing table scans (lock escalation)
- **Resolution**: Standardize transaction order, add indexes, reduce isolation level, optimize query
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的锁竞争诊断路径

### Rule 5: Geo-Replication Lag High
- **Trigger**: `geo_replication_lag` > 60s for > 10min
- **Diagnostic Steps**:
  1. Check primary-secondary connectivity: `sys.dm_geo_replication_link_status`
  2. Verify network bandwidth between regions
  3. Check secondary workload: read-only queries blocking replication
  4. Check primary write volume: sustained high write rate
  5. Review geo-replication configuration
- **Root Causes**:
  - Network bandwidth bottleneck between regions
  - Secondary overloaded with read workload
  - Primary write volume exceeding replication capacity
  - Geo-replication throttling (tier limit)
- **Resolution**: Reduce primary write volume, offload read from secondary, upgrade tier, check network
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的跨区域诊断路径

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

## Cross-Skill Integration

- 相关 Skill: `azure-monitor-ops` (诊断日志、Activity Log 深度分析)
- 标准诊断路径: `docs/cross-skill-rca-schema.md`
