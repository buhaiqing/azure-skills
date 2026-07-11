# Azure SQL Database Troubleshooting and RCA

## Method: Evidence Before Conclusion

Do not start with a fix. Collect evidence in this order:

1. Confirm subscription, Resource Group, server name, FQDN, version, state, service objective, Max Size, and networking mode.
2. Build incident timeline: symptom start, deployments, restart/stop/start, scale, firewall/private-access changes, parameter changes.
3. Query SQL DB metrics for `{{user.analysis_window}}` and compare with a previous healthy window.
4. Check Activity Log for configuration and lifecycle changes.
5. Inspect diagnostic logs, Query Store, or `sys.dm_*` views if enabled (DBA-assisted).
6. Rank root-cause candidates by evidence and confidence.
7. Separate safe diagnostics from remediation needing confirmation or DBA review.

## Symptom Index

| Symptom | First Evidence | Likely Area |
|---------|----------------|-------------|
| Login failures (`18456`) | `connection_failed`, firewall rules, server state, AAD/admin config | auth, firewall, AAD admin, password/secret rotation |
| `40814` / no route to server | `blocked_by_firewall`, private DNS, network config | firewall rule missing, private DNS, NSG, route |
| Connection timeout | `connection_failed`, network metrics, restart timing | firewall, DNS, transient, pool exhaustion |
| Sessions/workers high | `sessions_percent`, `workers_percent` | pool leak, pool sizing, long sessions |
| DTU/CPU high | `dtu_consumption_percent`, `cpu_percent`, top queries | missing index, plan change, workload surge |
| Storage near full | `storage_percent`, `storage` | data growth, transaction-log pressure, autovacuum-equivalent lag |
| Blocking / deadlocks | `deadlock`, blocking session evidence | transaction ordering, lock contention |
| Slow queries | logs, Query Store, DBA `sys.dm_exec_*` | query plan, index, stats, locks |
| Long transactions | DBA-provided DB views | lock retention, log growth |
| Tempdb pressure | `tempdb_log_used_percent`, temp-table spills | sort/hash spills, workload, SKU limit |

## Common Error Codes

| Code | Meaning | First Check |
|------|---------|--------------|
| `18456` | Login failed for user | correct login name, password/secret valid, AAD admin set, server not blocked by firewall |
| `4060` | Cannot open database requested | DB name correct, DB online, user has CONNECT |
| `40814` | No route to server from client subnet | firewall rule for client IP, or private DNS/NSG if private endpoint |
| `4230` / `10928` / `10929` | Resource limit / throttling (DTU/eDTU) | scale up or tune workload |
| `40549` / `40551` | Session/worker killed due to resource limit | reduce concurrency |
| `40552` | Transaction log exceeded; session killed | autocommit/transaction size, log pressure |
| `49918` / `49919` | Server busy / provisioning conflict | retry; check LRO state |
| `8651` / `8645` | Could not get memory / plan aborted | memory pressure, parameterize queries |
| `1205` | Deadlock victim | transaction ordering, lock scope |
| `1222` | Lock request timeout | blocking session, long transaction |
| Timeout (client) | No server response within threshold | firewall/DNS, transient, connection-pool exhaustion |

## Triage Commands

```bash
az sql server show \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,state:state,fqdn:fullyQualifiedDomainName,version:version,publicAccess:publicNetworkAccess}" \
  --output json

az sql db show \
  --name "{{user.database_name}}" \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,status:status,objective:currentServiceObjectiveName,maxSize:maxSizeBytes,elasticPool:elasticPoolName}" \
  --output json

az monitor metrics list \
  --resource "{{output.server_id}}" \
  --metric "dtu_consumption_percent,cpu_percent,storage_percent,storage,sessions_percent,workers_percent,connection_failed,deadlock" \
  --interval PT1M \
  --aggregation Average,Maximum,Total \
  --output json

az monitor activity-log list \
  --resource-group "{{user.resource_group}}" \
  --resource-id "{{output.server_id}}" \
  --offset "{{user.analysis_window}}" \
  --output json
```

If a metric name fails, run `az monitor metrics list-definitions --resource "{{output.server_id}}" --output json` and retry with verified names. Database-scoped metrics use `{{output.database_id}}`.

## Root Cause Rules

| Rule | Evidence Pattern | Confidence |
|------|------------------|------------|
| Missing index / bad plan | CPU/DTU high + slow-query evidence + high rows scanned | Medium; High with Query Store/plan evidence |
| Connection pool leak | `sessions_percent`/`workers_percent` grows while CPU/IO not proportional | High if app deploy aligns |
| Pool undersized / surge | sessions/workers + CPU/DTU rise with traffic | Medium |
| Firewall / private DNS issue | failed connections + firewall/private-access change or `blocked_by_firewall` | High |
| Auth / credential issue | failed logins after password/secret rotation or AAD admin change | High |
| Storage / log pressure | `storage_percent` rises, `tempdb_log_used_percent` high | Medium; DBA evidence required |
| Lock contention | slow queries + deadlocks/blocking + long transactions | High with DB evidence |
| Throttling (DTU limit) | `dtu_consumption_percent` pegged + `10928`/`10929` | High |
| Restart cold cache | latency/CPU changes after restart, improves over time | Medium |
| Parameter change regression | performance changes after server parameter update | High if Activity Log aligns |

## Correlation Playbooks

### Connection / Login Failures

1. Confirm server state and FQDN.
2. Check firewall rules or private-access configuration.
3. Correlate failed connections with Activity Log changes and AAD admin state.
4. Ask user to run client-side DNS/connectivity test from affected network if private access is involved.
5. If auth suspected, do not request password; ask user to validate secret source and recent rotations.

Safe actions:
- show server/network config;
- list firewall rules;
- query failed-connection metrics;
- query Activity Log.

Requires confirmation:
- firewall changes;
- private networking changes;
- server start/stop.

### DTU/CPU High / Slow Queries

1. Check DTU/CPU, sessions, workers, storage, deadlocks.
2. Check diagnostic logs / Query Store if enabled.
3. Ask DBA/app owner for top SQL or `sys.dm_exec_query_stats` output if logs unavailable.
4. Identify whether root cause is query plan, missing index, lock contention, or traffic surge.

Safe actions:
- collect metrics/logs;
- recommend `SET STATISTICS`/plan review in non-production or safe window;
- recommend stats/index review.

Requires DBA review:
- create/drop index;
- rewrite T-SQL;
- kill sessions;
- change server parameters.

### Storage / Transaction-Log Pressure

1. Check `storage_percent` trend and growth rate.
2. Correlate with log growth, tempdb pressure, long transactions, or bulk load window.
3. Check Max Size and whether growth is safe.
4. Recommend immediate safe actions and longer-term DBA actions.

Safe actions:
- collect metrics;
- identify growth window;
- request DBA table/log evidence.

Requires confirmation:
- shrink/scale storage;
- server start/stop;
- data purge;
- DDL/index maintenance.

### Blocking / Deadlocks

1. Check `deadlock` metric and blocking evidence.
2. Correlate with deployment or workload batch.
3. Request blocked-session and query samples from DBA if not available.
4. Recommend transaction-ordering and lock-scope review.

Do not kill sessions automatically.

## Decision Matrix

| Finding | Action |
|---------|--------|
| Strong evidence, safe diagnostic | Execute and report |
| Strong evidence, T-SQL/DDL remediation | Produce DBA review item; do not execute |
| Medium evidence, disruptive remediation | Recommend approval-gated action; do not execute |
| Low evidence | Collect more logs/metrics or escalate |
| User asks to skip confirmation | Refuse and HALT |

## RCA Report Template

```text
Incident summary: <what happened and impact>
Timeline: <start, peak, recent changes>
Metric anomalies: <metrics, values, baseline comparison>
Query/log evidence: <logs, Query Store, DBA-provided evidence>
Likely root causes:
1. <cause> — Confidence: High|Medium|Low — Evidence: <evidence>
2. <cause> — Confidence: High|Medium|Low — Evidence: <evidence>
Immediate safe checks:
- <read-only diagnostic>
Risky remediation needing approval:
- <operation, expected impact, rollback/mitigation>
DBA review items:
- <T-SQL/index/parameter/session recommendation>
Escalation criteria:
- <when to involve Azure Support/DBA/network/app team>
```

## Escalation Criteria

Escalate when:
- repeated Azure 5xx/control-plane errors include correlation IDs;
- database-level evidence requires DBA-only access (`sys.dm_*` views, Query Store);
- private-access evidence requires network owner access;
- storage is critically high and safe evidence is insufficient;
- DDL, session kill, server start/stop, or production scale is requested;
- symptoms affect multiple systems and SQL DB evidence is inconclusive.
