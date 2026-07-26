# Azure PostgreSQL AIOps Analysis

## Detection Signals

| Signal | Source | Threshold | Severity |
|--------|--------|-----------|----------|
| pg_connection_failed | `az monitor metrics list` --metric "connections_failed" | > baseline 2x or sustained nonzero | High |
| pg_cpu_high | `az monitor metrics list` --metric "cpu_percent" | sustained > 80% or > 2x baseline | High |
| pg_memory_pressure | `az monitor metrics list` --metric "memory_percent" | sustained > 80% or sharp rise | Medium |
| pg_storage_high | `az monitor metrics list` --metric "storage_percent" | > 85% or fast growth trend | Critical |
| pg_replication_lag | `az postgres flexible-server replica list` | rising lag or > threshold (read replicas) | High |
| pg_iops_throttled | `az monitor metrics list` --metric "iops" | > 2x baseline with query latency | Medium |
| pg_deadlock_detected | `az monitor metrics list` --metric "deadlocks" | nonzero or above baseline | Medium |
| pg_query_latency_high | Query Store / `pg_stat_statements` | query time > 5s or > baseline 3x | High |

## Purpose

AIOps in this skill means metric anomaly detection, evidence correlation, query/log signal ranking, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Inputs

| Input | Source |
|-------|--------|
| Server state/config | `az postgres flexible-server show` |
| Metrics | Azure Monitor metrics |
| Activity timeline | Activity Log, delegate deep audit to `azure-monitor-ops` (see `docs/cross-skill-rca-schema.md`) |
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

## RCA Rules

### Rule 1: Connection Timeout / Refused
- **Trigger**: `pg_connection_failed` detected OR application reports "connection timeout" / "connection refused"
- **Diagnostic Steps**:
  1. Check server state: `az postgres flexible-server show --name <server> --resource-group <rg>`
  2. Check firewall rules: `az postgres flexible-server firewall-rule list --name <server> --resource-group <rg>`
  3. Check private access: `az postgres flexible-server show --name <server> --resource-group <rg> --query "network"`
  4. Check active connections: `az monitor metrics list --resource <server_id> --metric "active_connections"`
  5. Check Activity Log for recent firewall/network changes
- **Root Causes**:
  - Client IP not in firewall rules
  - Private endpoint misconfigured or NSG blocking
  - Connection limit reached
  - Server stopped or paused
  - Authentication failure (wrong password, expired secret)
- **Resolution**:
  - Add client IP to firewall rules (with confirmation)
  - Verify private endpoint and NSG rules
  - Scale up or increase connection limit (requires parameter update)
  - Restart server if stopped
  - Rotate secrets if authentication issue
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的 "Database Performance Degradation" 诊断路径

### Rule 2: CPU / Memory Pressure
- **Trigger**: `pg_cpu_high` OR `pg_memory_pressure` detected
- **Diagnostic Steps**:
  1. Check current metrics: `az monitor metrics list --resource <server_id> --metric "cpu_percent,memory_percent"`
  2. Correlate with query performance via Query Store or `pg_stat_statements`
  3. Check for recent workload changes in Activity Log
  4. Check for parameter changes that may affect query plans
  5. Compare with baseline (same hour previous day/week)
- **Root Causes**:
  - Slow query or missing index
  - Query plan change (statistics outdated, parameter change)
  - Workload surge (traffic spike, batch job)
  - SKU undersized for workload
  - Sort/hash spill to disk (memory insufficient)
- **Resolution**:
  - Identify and tune top resource-consuming queries (DBA review required)
  - Update statistics or create missing indexes
  - Scale up SKU (compute tier or vCores)
  - Adjust memory-related parameters (work_mem, shared_buffers)
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的 "Database Performance Degradation" 诊断路径

### Rule 3: Storage Space Exhaustion
- **Trigger**: `pg_storage_high` detected (storage_percent > 85%)
- **Diagnostic Steps**:
  1. Check current storage metrics: `az monitor metrics list --resource <server_id> --metric "storage_percent,storage_used"`
  2. Check growth rate over past 6 hours and 24 hours
  3. Identify storage consumers: WAL retention, temp files, table/index bloat
  4. Check autovacuum status via `pg_stat_user_tables`
  5. Check for long-running transactions blocking vacuum
- **Root Causes**:
  - Data growth (normal or unexpected bulk load)
  - WAL file accumulation (replication lag, long backup)
  - Table/index bloat (autovacuum lag, long transactions)
  - Temp file growth (large sorts/hashes)
  - Storage tier undersized
- **Resolution**:
  - Increase storage tier (if storage-autogrow enabled, verify limit)
  - Tuning autovacuum parameters or manually vacuum tables
  - Identify and terminate long-running transactions blocking vacuum
  - Add storage or scale storage tier
  - Review and optimize queries causing temp file growth
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的 "Database Performance Degradation" 诊断路径

### Rule 4: Replication Lag (Read Replicas)
- **Trigger**: `pg_replication_lag` rising OR replica query latency increased
- **Diagnostic Steps**:
  1. Check replica status: `az postgres flexible-server replica list --name <server> --resource-group <rg>`
  2. Check replication lag metrics on primary and replica
  3. Check replica CPU/memory/IOPS metrics
  4. Check network latency between primary and replica
  5. Check for long-running queries on replica
- **Root Causes**:
  - Replica undersized (CPU/memory/IOPS)
  - Network bottleneck between primary and replica
  - Long-running queries on replica blocking replay
  - Checkpoint or WAL backlog on primary
- **Resolution**:
  - Scale up replica SKU
  - Optimize or terminate long-running queries on replica
  - Check and fix network issues
  - Adjust primary checkpoint parameters (with DBA review)
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的 "Database Performance Degradation" 诊断路径

### Rule 5: Query Performance Degradation
- **Trigger**: `pg_query_latency_high` detected OR user reports slow queries
- **Diagnostic Steps**:
  1. Check Query Store or `pg_stat_statements` for top queries by total_time, rows_scanned, temp_usage
  2. Run `EXPLAIN ANALYZE` on suspect queries (DBA review required)
  3. Check for recent statistics updates (autovacuum analyze)
  4. Check for index bloat or missing indexes
  5. Check for lock contention: `pg_locks` and `pg_stat_activity`
- **Root Causes**:
  - Missing or unused indexes
  - Outdated statistics causing poor query plans
  - Index or table bloat
  - Lock contention (long transactions, explicit locks)
  - Query plan regression (parameter change, stats change)
- **Resolution**:
  - Create missing indexes (DBA review required)
  - Update statistics: `ANALYZE` or autovacuum analyze
  - Rebuild bloated indexes or vacuum tables
  - Tune queries or application logic
  - Adjust query-related parameters (with DBA review)
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的 "Database Performance Degradation" 诊断路径

### Rule 6: IOPS Throttling
- **Trigger**: `pg_iops_throttled` detected OR query latency spikes correlate with IOPS saturation
- **Diagnostic Steps**:
  1. Check IOPS metrics: `az monitor metrics list --resource <server_id> --metric "iops"`
  2. Correlate with query activity: Query Store, `pg_stat_statements`
  3. Check for checkpoint spikes in logs
  4. Check for autovacuum activity
  5. Compare IOPS tier limit with observed throughput
- **Root Causes**:
  - Scan-heavy queries (sequential scans, missing indexes)
  - Table/index bloat increasing scan workload
  - Checkpoint pressure (large checkpoint bursts)
  - Autovacuum I/O contention
  - IOPS tier undersized for workload
- **Resolution**:
  - Optimize scan-heavy queries with indexes
  - Reduce bloat via vacuum/reindex
  - Tune checkpoint parameters (spread checkpoints)
  - Adjust autovacuum I/O limit parameters
  - Scale up IOPS tier or move to Premium SSD
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的 "Database Performance Degradation" 诊断路径

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

## Cross-Skill Integration
- 相关 Skill: azure-monitor-ops（诊断日志、Activity Log 深度分析）
- 跨 skill RCA 路径: 参考 `docs/cross-skill-rca-schema.md` 的 "Database Performance Degradation" 标准诊断路径
- 当本 skill 检测到异常涉及其他服务时:
  - 委托 `azure-monitor-ops` 进行指标关联和 Activity Log 调查
  - 如果应用在 VM 上，委托 `azure-vm-ops` 检查应用到数据库的连接池状态
  - 如果应用在 App Service 上，委托 `azure-appservice-ops` 检查应用性能和依赖项延迟
