# Azure Cosmos DB AIOps Analysis

## Purpose

AIOps in this skill means metric anomaly detection, evidence correlation, per-partition signal ranking, root-cause ranking, and risk-ranked recommendations around RU/s, throttling, partition skew, and global distribution. It must not perform remediation automatically.

## Inputs

| Input | Source |
|-------|--------|
| Account state/config | `az cosmosdb show` |
| Metrics | Azure Monitor metrics |
| Activity timeline | Activity Log, delegate deep audit to `azure-monitor-ops` (see `docs/cross-skill-rca-schema.md`) |
| Diagnostic logs | Log Analytics if enabled; delegate complex KQL to `azure-monitor-ops` |
| Per-partition metrics | PartitionKeyRUConsumption / PartitionKeyStorage if enabled |
| User incident context | symptom, start time, impacted clients, recent deploys |

## Analysis Windows

| Window | Use |
|--------|-----|
| `PT1H` | Active incident, high-resolution triage |
| `PT6H` | Incident evolution and recent changes |
| `P1D` | Capacity/RU/s trend and daily pattern |
| Baseline same hour previous day/week | Avoid false positives from normal traffic cycles |

## Metric Collection

```bash
az monitor metrics list \
  --resource "{{output.account_id}}" \
  --metric "TotalRequestUnits,NormalizedRUConsumption,ThrottleRate,ProvisionedThroughput,DataUsage,AvailableStorage" \
  --interval PT1M \
  --aggregation Average,Maximum,Total \
  --start-time "{{user.start_time}}" \
  --end-time "{{user.end_time}}" \
  --output json
```

If exact metrics differ, query definitions first and map equivalent metrics.

建议先按症状分组，再用 PT5M 粒度粗扫，缩小时间窗后切换 PT1M。

## Detection Signals

| Signal | Source | Threshold | Severity |
|--------|--------|-----------|----------|
| Normalized RU high | Azure Monitor `NormalizedRUConsumption` | sustained > 80% for > 10min or > 2x baseline | High |
| ThrottleRate high | Azure Monitor `ThrottleRate` | nonzero or > 10 req/min sustained | Critical |
| Storage quota approaching | Azure Monitor `AvailableStorage` | < 15% of provisioned storage | High |
| Cross-region latency spike | Azure Monitor `ReplicationLatency` | > 500ms for > 5min (multi-region) | Medium |
| Connection timeout | Application logs / Azure Monitor | Timeout errors > 1% of requests | High |
| Index utilization low | Diagnostic logs `IndexUtilizationScore` | < 30% on frequent queries | Medium |
| Partition skew | `PartitionKeyRUConsumption` / `PartitionKeyStorage` | single partition > 5x average | High |

## Anomaly Rules

| Signal | Detection Rule | Root-Cause Candidates |
|--------|----------------|-----------------------|
| Normalized RU high | sustained > 80% or > 2x baseline | under-provisioned RU/s, hot partition, burst |
| ThrottleRate high | nonzero or above baseline | RU/s saturation, partition skew |
| TotalRequestUnits high | > 2x baseline | query inefficiency, volume, skew |
| Storage high | > 85% or fast growth | large items, no TTL, unbounded growth |
| AvailableStorage low | approaching physical partition limit | storage split needed, archive |
| Cross-region latency | reads from non-write region + strong consistency | region endpoint, consistency |
| Replication conflict | nonzero conflicts with multi-region writes | conflict policy, write pattern |

## RCA Rules

### Rule 1: Request Rate Limiting (429 Too Many Requests)
- **Trigger**: ThrottleRate > 0 sustained for > 5min, or NormalizedRUConsumption > 80%
- **Diagnostic Steps**:
  1. Check RU/s provisioning: `az cosmosdb show --name <account> --resource-group <rg> --query "properties.resource.ruPerSecond"`
  2. Check per-partition RU consumption: Query `PartitionKeyRUConsumption` metric for hot partition identification
  3. Check autoscale status: `az cosmosdb show --query "properties.resource.autoscaleSettings"` to verify if autoscale is enabled
  4. Correlate with recent changes: Query Activity Log for RU/s scale-down or container changes within 30min
- **Root Causes**:
  - RU/s under-provisioned for current workload
  - Hot partition (single partition key dominates traffic)
  - Query inefficiency (missing index, cross-partition queries)
  - Burst traffic exceeding autoscale max
- **Resolution**: Increase RU/s (manual or raise autoscale max); if hot partition, redesign partition key; optimize queries
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 2: Connection Timeout
- **Trigger**: Connection timeout errors > 1% of requests, or `ServiceAvailability` metric drops below 99.9%
- **Diagnostic Steps**:
  1. Check account status: `az cosmosdb show --query "properties.provisioningState"` for service health
  2. Check network connectivity: Verify VNet/subnet restrictions if using private endpoints
  3. Check region availability: `az cosmosdb show --query "properties.readLocations"` for multi-region issues
  4. Check consistency level: Strong consistency may increase latency for cross-region reads
- **Root Causes**:
  - Network/firewall blocking SDK endpoints (DNS resolution, port 443)
  - Service-side throttling or outage
  - Client-side connection pool exhaustion
  - Multi-region replication lag with strong consistency
- **Resolution**: Verify network rules; check Azure status page; review SDK connection policy; consider relaxing consistency for non-critical reads
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 3: Storage Quota Exceeded
- **Trigger**: AvailableStorage < 15% of provisioned storage, or storage > 85% capacity
- **Diagnostic Steps**:
  1. Check storage usage: `az monitor metrics list --metric "DataUsage,AvailableStorage"` for account/container level
  2. Check per-partition storage: Query `PartitionKeyStorage` metric for uneven distribution
  3. Check TTL configuration: `az cosmosdb sql container show --query "resource.defaultTtl"` for missing TTL
  4. Check item size distribution: Review diagnostic logs for large items (> 2MB each)
- **Root Causes**:
  - Unbounded data growth (missing TTL, no archival policy)
  - Hot partition with skewed storage distribution
  - Large item sizes (attachments, embedded arrays)
  - Physical partition storage limit reached (20GB per physical partition in some cases)
- **Resolution**: Enable TTL; archive old data to blob storage; redesign partition key for even distribution; split container if needed
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 4: Replication Latency (Multi-Region)
- **Trigger**: ReplicationLatency > 500ms sustained, or cross-region read latency > 2x baseline
- **Diagnostic Steps**:
  1. Check replication health: `az cosmosdb show --query "properties.readLocations"` for region status
  2. Check consistency level: `az cosmosdb show --query "properties.consistencyPolicy.defaultConsistencyLevel"` (Strong/BoundedStaleness increases latency)
  3. Check write region load: High RU consumption in write region delays replication
  4. Check network between regions: Azure Monitor `NetworkLatency` for inter-region connectivity
- **Root Causes**:
  - Strong consistency forcing synchronous cross-region commits
  - Write region overloaded, slowing replication pipeline
  - Network latency between regions
  - Read region failover or maintenance
- **Resolution**: Consider BoundedStaleness or Session consistency for lower latency; scale write region RU/s; add read region closer to users
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

## Correlation Rules

### Change Correlation

If anomaly start is within 30 minutes after Activity Log or deployment event, increase confidence for that event as a cause.

High-risk change categories:
- RU/s scale down / autoscale max reduction;
- partition key / container recreate;
- consistency level change;
- region add/remove / failover;
- key regenerate;
- application deployment reported by user.

### RU/s Correlation

If NormalizedRUConsumption and ThrottleRate rise together, classify throughput saturation as a candidate before blaming the app. If only one partition key dominates, classify hot partition.

### Partition Correlation

If one logical partition consumes disproportionate RU/storage while account NormalizedRU is moderate, prioritize partition key redesign over blanket RU/s increase.

### Storage Correlation

If storage grows quickly while user reports no data growth, prioritize missing TTL, large item size, and unbounded collections over RU/s.

### Region Correlation

If latency rises after a region change or reads hit a distant region, prioritize endpoint/consistency review over RU/s scaling.

## Confidence Scoring

| Level | Requirement |
|-------|-------------|
| High | Metrics, diagnostics/per-partition evidence, and timeline agree |
| Medium | Metrics match symptom and timeline, but per-partition/log evidence is missing |
| Low | Single signal or weak timing; more evidence needed |

Never present low-confidence hypotheses as facts.

## Risk-Ranked Recommendation Model

| Risk | Examples | Agent Behavior |
|------|----------|----------------|
| Safe | read metrics, show config, list keys metadata, query Activity Log | execute directly |
| Low | enable additional diagnostic collection when non-disruptive | ask if cost/noise impact unclear |
| Medium | RU/s increase, region add, consistency relax, autoscale max raise | require confirmation and rollback note |
| High | delete, key regenerate, consistency change in production, region remove/failover, RU/s scale down, partition key recreate, broad network change | require explicit confirmation; data-plane changes require DBA/app review |

## DBA/App Review Items

Use this format for database-level recommendations:

```text
DBA/app review item: <partition key / index / query / TTL topic>
Evidence: <metric/diagnostic/per-partition signal>
Suggested validation: <query diagnostics, partition stats, explain>
Risk: <hot partition, storage split, downtime on recreate>
Do not execute automatically: true
```

## AIOps Report Template

```text
Incident: <short title>
Window analyzed: <start/end + baseline>
Anomalies:
- <metric>: <observed> vs <baseline>, time <window>
Correlations:
- <Activity Log/config/app/per-partition event> within <minutes> of anomaly
Root-cause candidates:
1. <candidate> — Confidence: High|Medium|Low — Evidence: <evidence>
2. <candidate> — Confidence: High|Medium|Low — Evidence: <evidence>
Safe checks completed:
- <command/result summary>
Recommended next actions:
- Safe: <diagnostic>
- Approval required: <operation + impact>
DBA/app review:
- <partition key / index / query / TTL item>
Escalation:
- <team/support condition>
```

## Guardrails

- Do not claim causality from correlation alone.
- Do not delete accounts/containers, regenerate keys, change consistency/failover, remove regions, scale down RU/s, or recreate containers with new partition keys as part of AIOps.
- Do not request or expose account keys or connection strings.
- Mask any accidentally returned credential-like value as `***`.
- If evidence is insufficient, state what evidence is missing.

## Cross-Skill Integration

- 相关 Skill: azure-monitor-ops（诊断日志、Activity Log）、azure-aks-ops（容器应用访问 Cosmos DB）
- 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径
