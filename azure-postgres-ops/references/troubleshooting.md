# Azure PostgreSQL Troubleshooting and RCA

## Method: Evidence Before Conclusion

Do not start with a fix. Collect evidence in this order:

1. Confirm subscription, Resource Group, server name, SKU, Location, state, HA, storage, and networking mode.
2. Build incident timeline: symptom start, deployments, restart/stop/start, scale, firewall/private access changes, parameter changes.
3. Query PostgreSQL metrics for `{{user.analysis_window}}` and compare with a previous healthy window.
4. Check Activity Log for configuration and lifecycle changes.
5. Inspect diagnostic logs, Query Store, or `pg_stat_statements` if enabled.
6. Rank root-cause candidates by evidence and confidence.
7. Separate safe diagnostics from remediation needing confirmation or DBA review.

## Symptom Index

| Symptom | First Evidence | Likely Area |
|---------|----------------|-------------|
| Connection failures | connections_failed, firewall rules, server state | auth, firewall, DNS, private access |
| Active connections high | active_connections, app deploy timing | pool leak, pool sizing, long sessions |
| CPU high | cpu_percent, top queries | missing index, plan change, workload surge |
| Memory pressure | memory_percent, temp files | sort/hash spills, workload, SKU limit |
| IOPS high | IOPS metrics, slow queries | scans, bloat, checkpoint/write pressure |
| Storage near full | storage_percent, WAL/temp growth | bloat, WAL retention, autovacuum lag |
| Deadlocks | deadlocks metric/logs | transaction ordering, lock contention |
| Slow queries | logs, Query Store, pg_stat_statements | query plan, index, stats, locks |
| Long transactions | logs/DB views from DBA | vacuum lag, bloat, lock retention |
| Replication lag / HA issues | lag metrics, HA state | replica pressure, network, storage |

## Triage Commands

```bash
az postgres flexible-server show \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,state:state,fqdn:fullyQualifiedDomainName,sku:sku.name,version:version,storage:storage.storageSizeGb,ha:highAvailability.state}" \
  --output json

az monitor metrics list \
  --resource "{{output.server_id}}" \
  --metric "cpu_percent,memory_percent,storage_percent,active_connections,connections_failed,iops,deadlocks" \
  --interval PT1M \
  --aggregation Average,Maximum,Total \
  --output json

az monitor activity-log list \
  --resource-group "{{user.resource_group}}" \
  --resource-id "{{output.server_id}}" \
  --offset "{{user.analysis_window}}" \
  --output json
```

If a metric name fails, run `az monitor metrics list-definitions --resource "{{output.server_id}}" --output json` and retry with verified names.

## Root Cause Rules

| Rule | Evidence Pattern | Confidence |
|------|------------------|------------|
| Missing index / bad query plan | CPU high + slow query evidence + high rows scanned | Medium; High with EXPLAIN/Query Store evidence |
| Connection pool leak | active_connections grows steadily while CPU/IO not proportional | High if app deploy aligns |
| Pool undersized/traffic surge | active_connections + CPU/IO rise with traffic | Medium |
| Firewall/private DNS issue | failed connections + firewall/private access change | High |
| Auth/credential issue | failed connections after password/secret rotation | High |
| Storage pressure from bloat | storage grows while business data growth unclear + vacuum lag | Medium; DBA evidence required |
| WAL retention/log growth | storage grows quickly after replication/backup/log issue | Medium |
| Autovacuum lag | bloat/storage/WAL + long transactions | Medium; High with DB views |
| Lock contention | slow queries + deadlocks/locks + long transactions | High with DB evidence |
| IOPS saturation | high IOPS + slow queries + read/write latency | Medium |
| Restart cold cache | latency/CPU changes after restart, improves over time | Medium |
| Parameter change regression | performance changes after server parameter update | High if Activity Log aligns |

## Correlation Playbooks

### Connection Failures

1. Confirm server state and FQDN.
2. Check firewall rules or private access configuration.
3. Correlate failed connections with Activity Log changes.
4. Ask user to run client-side DNS/connectivity test from affected network if private access is involved.
5. If auth suspected, do not request password; ask user to validate secret source and recent rotations.

Safe actions:
- show server/network config;
- list firewall rules;
- query failed connection metrics;
- query Activity Log.

Requires confirmation:
- firewall changes;
- private networking changes;
- restart.

### CPU High / Slow Queries

1. Check CPU, active connections, IOPS, memory, and deadlocks.
2. Check diagnostic logs/Query Store if enabled.
3. Ask DBA/app owner for top SQL or `pg_stat_statements` output if logs are unavailable.
4. Identify whether root cause is query plan, missing index, lock contention, or traffic surge.

Safe actions:
- collect metrics/logs;
- recommend EXPLAIN ANALYZE in non-production or safe window;
- recommend stats/vacuum/index review.

Requires DBA review:
- create/drop index;
- rewrite SQL;
- kill sessions;
- change server parameters.

### Storage Pressure

1. Check storage_percent trend and growth rate.
2. Correlate with WAL, temp files, autovacuum lag, long transactions, or bulk load window.
3. Check whether autogrow is enabled and whether maximum size is near.
4. Recommend immediate safe actions and longer-term DBA actions.

Safe actions:
- collect metrics;
- identify growth window;
- request DBA table/WAL/temp evidence.

Requires confirmation:
- storage scale;
- restart;
- data purge;
- DDL/index maintenance.

### Deadlocks / Lock Contention

1. Check deadlocks metric and logs.
2. Correlate with deployment or workload batch.
3. Request blocked session and query samples from DBA if not available.
4. Recommend transaction-ordering and lock-scope review.

Do not kill sessions automatically.

## Decision Matrix

| Finding | Action |
|---------|--------|
| Strong evidence, safe diagnostic | Execute and report |
| Strong evidence, SQL/DDL remediation | Produce DBA review item; do not execute |
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
- <SQL/index/parameter/session recommendation>
Escalation criteria:
- <when to involve Azure Support/DBA/network/app team>
```

## Escalation Criteria

Escalate when:
- repeated Azure 5xx/control-plane errors include correlation IDs;
- database-level evidence requires DBA-only access;
- private access evidence requires network owner access;
- storage is critically high and safe evidence is insufficient;
- DDL, session kill, failover-like action, or production restart is requested;
- symptoms affect multiple systems and PostgreSQL evidence is inconclusive.
