# Azure Event Hubs AIOps Analysis

## Purpose

AIOps in this skill means metric anomaly detection, evidence correlation, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Detection Signals

| Signal | Source | Threshold | Severity |
|--------|--------|-----------|----------|
| throughput_throttled | `az monitor metrics list` --metric "ThrottledRequests" | ThrottledRequests > 0 (baseline = 0) | High |
| bandwidth_near_limit | `az monitor metrics list` --metric "IncomingBytes" | Sustained > 80% TU/PU limit | High |
| consumer_lag_spike | `az monitor metrics list` --metric "ConsumerLag" | > 2x baseline within 5min | Medium |
| capture_backlog | `az monitor metrics list` --metric "CaptureBacklog" | Sustained > 0 and growing | Medium |
| partition_skew | `az monitor metrics list` --metric "ConsumerLag" (per-partition) | Variance > 50% across partitions | Medium |
| connection_drop | `az monitor metrics list` --metric "ActiveConnections" | Sharp decline > 30% within 5min | High |
| server_error_spike | `az monitor metrics list` --metric "ServerErrors" | > 2x baseline | High |

## Inputs

| Input | Source |
|-------|--------|
| Resource state | `az eventhubs namespace show`, `az eventhubs eventhub show` |
| Metrics | Azure Monitor metrics |
| Activity timeline | Activity Log, delegate deep audit to `azure-monitor-ops` (see `docs/cross-skill-rca-schema.md`) |
| Diagnostic logs | Log Analytics if enabled; delegate complex KQL to `azure-monitor-ops` |
| User incident context | symptom, start time, impacted producers/consumers, recent deploys |
| Client-side evidence | consumer lag, Kafka client logs, SDK error samples |

## Analysis Windows

| Window | Use |
|--------|-----|
| `PT1H` | Active incident, high-resolution triage |
| `PT6H` | Incident evolution and recent changes |
| `P1D` | Daily pattern, scale decision support |
| Baseline same hour previous day/week | Avoid false positives from normal traffic cycles |

## Metric Collection

```bash
az monitor metrics list \
  --resource "{{output.namespace_id}}" \
  --metric "ThrottledRequests,IncomingBytes,OutgoingBytes,IncomingMessages,OutgoingMessages,SuccessfulRequests,ServerErrors,UserErrors,ActiveConnections,CaptureBacklog" \
  --interval PT1M \
  --aggregation Average,Maximum,Total \
  --start-time "{{user.start_time}}" \
  --end-time "{{user.end_time}}" \
  --output json
```

For consumer lag, query at event hub level:

```bash
az monitor metrics list \
  --resource "{{output.eventhub_id}}" \
  --metric "ConsumerLag" \
  --interval PT1M \
  --aggregation Average,Maximum \
  --start-time "{{user.start_time}}" \
  --end-time "{{user.end_time}}" \
  --output json
```

If exact metrics differ by SKU, query definitions first and map equivalent metrics.

## Anomaly Rules

| Signal | Detection Rule | Root-Cause Candidates |
|--------|----------------|-----------------------|
| Throttling surge | `ThrottledRequests` > 0 when baseline is 0, or sharp increase | TU/PU capacity, auto-inflate off/maxed, partition skew |
| Bandwidth near limit | `IncomingBytes` sustained > 80% of TU/PU limit | capacity, scale need, partition skew |
| Consumer lag spike | `ConsumerLag` jumps significantly | consumer slowdown, partition count limit, hot partition |
| Capture backlog | `CaptureBacklog` sustained > 0 and growing | storage account issue, Capture IAM, Capture config |
| Error rate jump | `ServerErrors` or `UserErrors` > baseline by 2x | auth keys, RBAC, network, service issue |
| Connection drop | `ActiveConnections` sharp decline | firewall, private endpoint, producer/consumer restart |
| Partition skew | per-partition `ConsumerLag` variance > 50% | partition key design, hot partition |

## RCA Rules

### Rule 1: Throughput Throttling
- **Trigger**: `throughput_throttled` signal detected
- **Diagnostic Steps**:
  1. Check namespace capacity: `az eventhubs namespace show --name <namespace> --resource-group <rg>`
  2. Verify auto-inflate status: Check `capacity` and `autoInflateEnabled` properties
  3. Check partition distribution: `az monitor metrics list --resource <eventhub_id> --metric "ConsumerLag" --interval PT1M`
  4. Review recent scaling events: `az monitor activity-log list --resource-id <namespace_id> --start-time <1h_ago>`
- **Root Causes**:
  - TU/PU capacity insufficient for current traffic
  - Auto-inflate disabled or reached maximum threshold
  - Hot partition causing asymmetric load
  - Burst traffic exceeding capacity
- **Resolution**: Enable auto-inflate or manually increase TU/PU; optimize partition key design
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 2: Consumer Lag Spike
- **Trigger**: `consumer_lag_spike` signal detected
- **Diagnostic Steps**:
  1. Identify affected consumer groups: `az eventhubs eventhub consumer-group list --eventhub-name <eh> --namespace-name <ns> --resource-group <rg>`
  2. Check consumer instance health: Request client-side logs from application team
  3. Verify partition assignment: Check if consumer count >= partition count
  4. Analyze processing rate: `az monitor metrics list --resource <eventhub_id> --metric "OutgoingMessages" --interval PT1M`
- **Root Causes**:
  - Consumer application slowdown (CPU/memory bottleneck)
  - Insufficient consumer instances for partition count
  - Hot partition with uneven message distribution
  - Downstream dependency latency (database, API)
  - Consumer application crash or restart
- **Resolution**: Scale consumer instances; optimize downstream processing; rebalance partitions
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 3: Capture Failure
- **Trigger**: `capture_backlog` signal detected
- **Diagnostic Steps**:
  1. Verify Capture configuration: `az eventhubs eventhub show --name <eh> --namespace-name <ns> --resource-group <rg>`
  2. Check storage account accessibility: Delegate to `azure-blobstorage-ops` for storage diagnostics
  3. Verify IAM permissions: Check if Event Hubs namespace has Storage Blob Data Contributor role
  4. Check storage account metrics: `az monitor metrics list --resource <storage_id> --metric "Ingress,Transactions"`
- **Root Causes**:
  - Storage account throttling or unavailability
  - IAM permission revoked or missing
  - Storage account firewall blocking Event Hubs IP
  - Capture destination path misconfiguration
  - Storage account deleted or moved
- **Resolution**: Fix storage IAM; adjust storage throttling limits; verify network connectivity
- **Cross-Skill Integration**: 委托 `azure-blobstorage-ops` 诊断存储问题

### Rule 4: Connection Drop
- **Trigger**: `connection_drop` signal detected
- **Diagnostic Steps**:
  1. Check network security settings: `az eventhubs namespace show --name <ns> --resource-group <rg>` (check network rules)
  2. Verify private endpoint status: `az network private-endpoint show --name <pe> --resource-group <rg>`
  3. Check firewall rules: Review `networkAcls` in namespace properties
  4. Review authentication events: `az monitor activity-log list --resource-id <namespace_id> --start-time <1h_ago>`
- **Root Causes**:
  - Firewall rule changes blocking producer/consumer IPs
  - Private endpoint DNS resolution failure
  - Shared Access Key regeneration without client update
  - Network service interruption
  - Client-side certificate or credential expiration
- **Resolution**: Restore network rules; update client credentials; verify DNS resolution
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的网络诊断路径

### Rule 5: Partition Skew
- **Trigger**: `partition_skew` signal detected
- **Diagnostic Steps**:
  1. Analyze per-partition lag: `az monitor metrics list --resource <eventhub_id> --metric "ConsumerLag" --interval PT1M`
  2. Review partition key strategy: Request application team to provide partition key logic
  3. Check message distribution: `az monitor metrics list --resource <eventhub_id> --metric "IncomingMessages" --interval PT1M`
  4. Identify hot partition: Compare ConsumerLag across all partitions
- **Root Causes**:
  - Partition key design causing uneven distribution (e.g., userId without hash)
  - Hot key pattern in traffic (e.g., single tenant dominates)
  - Consumer group with unequal processing capacity
  - Insufficient partition count for traffic diversity
- **Resolution**: Redesign partition key with hash; increase partition count; rebalance consumers
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

## Correlation Rules

### Change Correlation

If anomaly start is within 30 minutes after an Activity Log event, increase confidence for that event as a cause.

High-risk change categories:
- namespace SKU/TU/PU change;
- key regeneration;
- Capture enable/disable;
- firewall/private endpoint update;
- event hub creation/deletion;
- app deployment reported by user.

### Dependency Correlation

If Capture backlog grows, check storage account metrics. If storage account is throttled or inaccessible, Capture will fall behind regardless of Event Hubs health. Delegate storage diagnostics to `azure-blobstorage-ops`.

If consumer lag grows and consumer instances are stable, suspect application processing bottleneck. Ask for consumer-side logs.

### Network Correlation

If connection errors rise but namespace metrics are normal, prioritize DNS, firewall, TLS, and private endpoint checks over namespace scaling.

## Confidence Scoring

| Level | Requirement |
|-------|-------------|
| High | Two or more independent evidence sources agree, and timeline matches |
| Medium | Metrics match symptom and timeline, but logs/client evidence are missing |
| Low | Single signal or weak timing; more evidence needed |

Never present low-confidence hypotheses as facts.

## Risk-Ranked Recommendation Model

| Risk | Examples | Agent Behavior |
|------|----------|----------------|
| Safe | read metrics, show namespace/event hub config, list consumer groups, query Activity Log | execute directly |
| Low | enable diagnostic logging when non-disruptive | ask if cost/noise impact unclear |
| Medium | increase TU/PU, enable auto-inflate, scale SKU | require confirmation and rollback note |
| High | delete namespace/event hub/consumer group, regenerate keys, disable Capture | require explicit confirmation; use GCL |

## AIOps Report Template

```text
Incident: <short title>
Window analyzed: <start/end + baseline>
Anomalies:
- <metric>: <observed> vs <baseline>, time <window>
Correlations:
- <Activity Log/config/app event> within <minutes> of anomaly
Root-cause candidates:
1. <candidate> — Confidence: High|Medium|Low — Evidence: <evidence>
2. <candidate> — Confidence: High|Medium|Low — Evidence: <evidence>
Safe checks completed:
- <command/result summary>
Recommended next actions:
- Safe: <diagnostic>
- Approval required: <operation + impact>
Escalation:
- <team/support condition>
```

## Guardrails

- Do not claim causality from correlation alone.
- Do not run destructive/disruptive commands as part of AIOps.
- Do not expose connection strings, access keys, or secrets in reports.
- Mask any accidentally returned credential-like value as `***`.
- If evidence is insufficient, state what evidence is missing.

## Cross-Skill Integration

- 相关 Skill: azure-monitor-ops（诊断日志、Activity Log）、azure-blobstorage-ops（Capture 存储诊断）
- 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径和跨服务根因分析链
- Capture 问题优先委托 `azure-blobstorage-ops` 检查存储账户状态
- 深度日志分析委托 `azure-monitor-ops` 执行 KQL 查询
