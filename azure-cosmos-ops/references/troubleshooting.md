# Azure Cosmos DB Troubleshooting and RCA

## Method: Evidence Before Conclusion

Do not start with a fix. Collect evidence in this order:

1. Confirm subscription, Resource Group, account name, API kind, Location, state, regions, consistency, RU/s.
2. Build incident timeline: symptom start, deployments, RU/s changes, region/consistency changes, key regenerate.
3. Query Cosmos metrics for `{{user.analysis_window}}` and compare with a previous healthy window.
4. Check Activity Log for configuration and lifecycle changes.
5. Inspect diagnostic logs / per-partition metrics if enabled.
6. Rank root-cause candidates by evidence and confidence.
7. Separate safe diagnostics from remediation needing confirmation or DBA review.

## Symptom Index

| Symptom | First Evidence | Likely Area |
|---------|----------------|-------------|
| 429 throttling | ThrottleRate, NormalizedRUConsumption, 429 count | under-provisioned RU/s, hot partition, burst |
| High RU consumption | TotalRequestUnits, NormalizedRUConsumption near 100% | query/index/volume, partition skew |
| Hot partition | PartitionKeyRUConsumption skew, single partition saturation | bad partition key choice |
| Storage near limit | DataUsage / AvailableStorage per physical partition | large items, no TTL, unbounded growth |
| High latency | TotalRequestCount by status, server-side throttling | RU pressure, cross-region read, consistency |
| Replication conflict | multi-region write conflicts, conflict metrics | multi-region writes, conflict policy |
| Connection failure | keys/connection string, network, private endpoint | auth, DNS, private access |
| Cross-region read slow | read region vs write region, consistency | wrong region endpoint, stale read |

## Triage Commands

```bash
az cosmosdb show \
  --name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,state:provisioningState,kind:kind,consistency:consistencyPolicy.defaultConsistencyLevel,locations:locations[].locationName}" \
  --output json

az monitor metrics list \
  --resource "{{output.account_id}}" \
  --metric "TotalRequestUnits,NormalizedRUConsumption,ThrottleRate,ProvisionedThroughput,DataUsage,AvailableStorage" \
  --interval PT1M \
  --aggregation Average,Maximum,Total \
  --output json

az monitor activity-log list \
  --resource-group "{{user.resource_group}}" \
  --resource-id "{{output.account_id}}" \
  --offset "{{user.analysis_window}}" \
  --output json
```

If a metric name fails, run `az monitor metrics list-definitions --resource "{{output.account_id}}" --output json` and retry with verified names.

建议先按症状分组，再用 PT5M 粒度粗扫，缩小时间窗后切换 PT1M。

## Root Cause Rules

| Rule | Evidence Pattern | Confidence |
|------|------------------|------------|
| Under-provisioned RU/s | NormalizedRUConsumption sustained high + 429s | High if matches throttle window |
| Hot partition | one partition key consumes disproportionate RU/storage | High with per-partition metrics |
| Bad partition key | high skew, single logical partition saturated | Medium; High with partition stats |
| Query/index inefficiency | high RU per request, full scans, no index | Medium; High with query diagnostics |
| Burst traffic | NormalizedRUConsumption spikes with traffic, no config change | Medium |
| Cross-region read penalty | reads served from non-write region, strong consistency | Medium |
| Consistency too strong | higher RU/latency than needed for workload | Medium with workload evidence |
| Storage growth / no TTL | DataUsage rising, AvailableStorage falling | Medium |
| Multi-region write conflict | conflict metric nonzero, conflict policy | Medium; High with conflict log |
| Key/network failure | failed connections after key regen / private endpoint change | High if Activity Log aligns |

## Correlation Playbooks

### 429 Throttling

1. Confirm NormalizedRUConsumption and ThrottleRate for the window.
2. Distinguish account-wide saturation vs single-partition (hot key) saturation.
3. Check whether RU/s was just reduced or autoscale max too low.
4. Recommend RU/s increase or partition key review — approval-gated if it changes production throughput.

Safe actions:
- show account/container config and RU/s;
- query throttle/normalized metrics;
- query Activity Log for throughput changes.

Requires confirmation:
- RU/s increase / autoscale max raise;
- changing partition key (recreate container);
- disabling autoscale on hot workload.

### Hot Partition / Skew

1. Check PartitionKeyRUConsumption / PartitionKeyStorage skew.
2. Identify the dominant logical partition value.
3. Recommend partition key redesign or synthetic/hierarchical key.

Safe actions:
- read metrics and container schema;
- recommend partition key candidate.

Requires DBA/app review:
- data migration to new partition key;
- container recreate with new key.

### Storage Pressure

1. Check DataUsage / AvailableStorage trends per physical partition.
2. Correlate with TTL settings, item size, unbounded growth.
3. Recommend TTL enablement or archival.

Safe actions:
- collect storage metrics;
- recommend TTL/index review.

Requires confirmation:
- large data purge;
- container recreate.

### Key / Connection Failure

1. Confirm account state and endpoint.
2. Check whether keys were regenerated or private endpoint changed.
3. Do not request keys; ask user to validate secret source and recent rotations.

Safe actions:
- show account network/key metadata;
- query Activity Log.

Requires confirmation:
- key regenerate;
- private networking changes (delegate `azure-privateendpoint-ops`).

## Decision Matrix

| Finding | Action |
|---------|--------|
| Strong evidence, safe diagnostic | Execute and report |
| Strong evidence, RU/s/partition remediation | Produce approval-gated / DBA review item; do not execute |
| Medium evidence, disruptive remediation | Recommend approval-gated action; do not execute |
| Low evidence | Collect more logs/metrics or escalate |
| User asks to skip confirmation | Refuse and HALT |

## RCA Report Template

```text
Incident summary: <what happened and impact>
Timeline: <start, peak, recent changes>
Metric anomalies: <metrics, values, baseline comparison>
Log/diagnostic evidence: <diagnostics, per-partition metrics, Activity Log>
Likely root causes:
1. <cause> — Confidence: High|Medium|Low — Evidence: <evidence>
2. <cause> — Confidence: High|Medium|Low — Evidence: <evidence>
Immediate safe checks:
- <read-only diagnostic>
Risky remediation needing approval:
- <operation, expected impact, rollback/mitigation>
DBA/app review items:
- <partition key / index / query / TTL recommendation>
Escalation criteria:
- <when to involve Azure Support/network/app team>
```

## Escalation Criteria

Escalate when:
- repeated Azure 5xx/control-plane errors include correlation IDs;
- evidence requires DBA-only data-plane access;
- private endpoint evidence requires network owner access;
- 429/throttling is sustained and safe evidence is insufficient;
- key regenerate, delete, consistency change, region change, or RU/s scale-down is requested in production;
- symptoms affect multiple systems and Cosmos evidence is inconclusive.
