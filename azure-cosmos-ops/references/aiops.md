# Azure Cosmos DB AIOps Analysis

## Purpose

AIOps in this skill means metric anomaly detection, evidence correlation, per-partition signal ranking, root-cause ranking, and risk-ranked recommendations around RU/s, throttling, partition skew, and global distribution. It must not perform remediation automatically.

## Inputs

| Input | Source |
|-------|--------|
| Account state/config | `az cosmosdb show` |
| Metrics | Azure Monitor metrics |
| Activity timeline | Activity Log, delegate deep audit to `azure-audit-ops` |
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
