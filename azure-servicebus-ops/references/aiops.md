# Azure Service Bus AIOps Analysis

## Purpose

AIOps in this skill means metric anomaly detection, evidence correlation, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Detection Signals

| Signal | Source | Threshold | Severity |
|--------|--------|-----------|----------|
| message_backlog_growth | `az monitor metrics list` --metric "ActiveMessages" | ActiveMessages > 10,000 或持续增长 > 15min | High |
| dlq_overflow | `az monitor metrics list` --metric "DeadletteredMessages" | DeadletteredMessages > 1,000 或增长率 > 100/hour | High |
| throttling_detected | `az monitor metrics list` --metric "ThrottledRequests" | ThrottledRequests > 0 | Critical |
| connection_limit_exceeded | `az servicebus namespace show` + metrics | Connections > SKU limit × 90% | High |
| throughput_saturation | `az monitor metrics list` --metric "IncomingMessages,OutgoingMessages" | Throughput > 80% of tier limit | Medium |
| message_latency_spike | `az monitor metrics list` + app logs | Message age > 5min in active queue | Medium |
| consumer_lag_detected | Consumer app metrics + `OutgoingMessages` | OutgoingMessages < 50% of IncomingMessages | High |

## Inputs

| Input | Source |
|-------|--------|
| Resource state | `az servicebus namespace show`, `az servicebus queue show`, `az servicebus topic show` |
| Metrics | Azure Monitor metrics |
| Activity timeline | Activity Log, delegate deep audit to `azure-monitor-ops` (see `docs/cross-skill-rca-schema.md`) |
| Diagnostic logs | Log Analytics if enabled; delegate complex KQL to `azure-monitor-ops` |
| User incident context | Symptom, start time, impacted clients, recent deploys |
| Client-side evidence | App logs, timeout/auth error samples, DLQ message inspection results |

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
  --metric "IncomingMessages,OutgoingMessages,ActiveMessages,DeadletteredMessages,SuccessfulRequests,ThrottledRequests,ServerErrors,UserErrors" \
  --interval PT5M \
  --aggregation Total,Average,Maximum \
  --start-time "{{user.start_time}}" \
  --end-time "{{user.end_time}}" \
  --output json
```

If exact metrics differ by SKU, query definitions first and map equivalent metrics.

## Anomaly Rules

| Signal | Detection Rule | Root-Cause Candidates |
|--------|----------------|-----------------------|
| DLQ growth | `DeadletteredMessages` > 0 when baseline is 0, or sustained increase | Poison messages, TTL expiry, delivery count exceeded, filter mismatch |
| Backlog accumulation | `ActiveMessages` rising faster than `OutgoingMessages` | Consumer scale, lock duration, processing errors, throttling |
| Throttling | `ThrottledRequests` > 0 | Throughput unit saturation, connection limit, quota exhaustion |
| Server errors | `ServerErrors` spike | Azure service issue, namespace unhealthy, throttling escalation |
| User errors | `UserErrors` spike | Auth failure, invalid message format, connectivity |
| Message throughput drop | `IncomingMessages` or `OutgoingMessages` drops > 50% | Producer/consumer offline, network issue, namespace degraded |
| Premium CPU/memory | `NamespaceCpuUsage` / `NamespaceMemoryUsage` > 80% | Capacity pressure, message volume surge |

## RCA Rules

### Rule 1: Message Backlog Accumulation
- **Trigger**: `message_backlog_growth` signal detected
- **Diagnostic Steps**:
  1. Check consumer health: `az monitor metrics list --metric "OutgoingMessages"` — identify if consumers stopped processing
  2. Inspect DLQ: `az servicebus queue show --name <queue> --resource-group <rg> --namespace <ns>` — check `countDetails.deadLetterMessageCount`
  3. Check throttling: `az monitor metrics list --metric "ThrottledRequests"` — determine if namespace is saturated
  4. Review consumer app logs: delegate to `azure-vm-ops`, `azure-aks-ops`, or `azure-appservice-ops` based on consumer deployment
- **Root Causes**:
  - Consumer application offline or crashed
  - Consumer processing errors causing message abandonment
  - Lock duration too short for processing time
  - Throughput limit hit (Standard tier: 1,000 concurrent connections, 40 MU/s)
  - Poison messages causing repeated failures
- **Resolution**: Scale consumer instances, increase lock duration, fix consumer processing errors, upgrade to Premium tier if throughput limit reached
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 2: Dead Letter Queue Overflow
- **Trigger**: `dlq_overflow` signal detected
- **Diagnostic Steps**:
  1. Inspect DLQ messages: `az servicebus queue show --name <queue> --resource-group <rg> --namespace <ns>` — get DLQ count
  2. Peek DLQ messages (requires SDK or portal): identify `deadLetterReason` and `deadLetterErrorDescription`
  3. Check queue config: `az servicebus queue show` — verify `maxDeliveryCount`, `defaultMessageTimeToLive`, `lockDuration`
  4. Review message TTL: ensure TTL > processing time
- **Root Causes**:
  - `MaxDeliveryCount exceeded`: consumer repeatedly failing to process
  - `TTL expired`: message older than queue's `defaultMessageTimeToLive`
  - `Filter mismatch` (topic subscription): subscription filter excludes all incoming messages
  - `Message size exceeded`: message > 256KB (Standard) or > 100MB (Premium)
  - `Session lock lost`: session-aware messages with lock timeout
- **Resolution**: Fix consumer processing errors, increase TTL, adjust subscription filters, implement message validation before send
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 3: Throttling and Throughput Saturation
- **Trigger**: `throttling_detected` or `throughput_saturation` signal detected
- **Diagnostic Steps**:
  1. Check throttling details: `az monitor metrics list --metric "ThrottledRequests"` — identify throttle type (throughput/connection/quota)
  2. Review namespace tier: `az servicebus namespace show` — verify SKU (Basic/Standard/Premium)
  3. Check connection count: `az monitor metrics list --metric "ConnectionsOpened"` — compare against tier limits
  4. Analyze throughput pattern: `az monitor metrics list --metric "IncomingMessages,OutgoingMessages"` — identify peak vs average
- **Root Causes**:
  - **Standard tier limits**: 40 MU/s per namespace, 1,000 concurrent connections, 100 topics/queues
  - **Premium tier under-provisioned**: insufficient messaging units (1, 2, 4, 8 MU options)
  - Connection leak: applications not closing connections properly (AMQP connection pooling issue)
  - Burst traffic: sudden spike exceeding allocated throughput
- **Resolution**:
  - **Immediate**: Scale Premium tier MU count (`az servicebus namespace update --capacity <MU>`)
  - **Long-term**: Migrate Standard to Premium, implement connection pooling, batch messages to reduce request count
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 4: Connection Limit Exceeded
- **Trigger**: `connection_limit_exceeded` signal detected
- **Diagnostic Steps**:
  1. Identify connection sources: `az monitor metrics list --metric "ConnectionsOpened"` — check connection count trend
  2. Review network rules: `az servicebus namespace network-rule-set show` — verify if IP filtering is correct
  3. Check consumer/producer deployment: correlate with recent app deployments (delegate to `azure-aks-ops` / `azure-appservice-ops`)
  4. Inspect connection leaks: enable diagnostic logs to track connection open/close events
- **Root Causes**:
  - Connection leak: applications creating new connections without closing old ones (common in AMQP clients)
  - Over-provisioned consumer/producer instances: too many instances each opening dedicated connections
  - Retry storm: failed connections triggering exponential backoff storms
  - Missing connection pooling: each thread/process creating dedicated connection
- **Resolution**: Implement AMQP connection pooling (single connection per process), fix connection leak in application code, reduce consumer/producer instance count if over-provisioned
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 5: Message Loss or Duplicate Processing
- **Trigger**: User reports missing messages or duplicates; `IncomingMessages` != `OutgoingMessages` + `ActiveMessages` + `DeadletteredMessages`
- **Diagnostic Steps**:
  1. Verify message flow: `az monitor metrics list --metric "IncomingMessages,OutgoingMessages,ActiveMessages,DeadletteredMessages"` — check message count consistency
  2. Check auto-delete settings: `az servicebus queue show` — verify `enableExpress`, `autoDeleteOnIdle`
  3. Inspect subscription filters: `az servicebus topic subscription show` — verify no unintended filters
  4. Review consumer acknowledgments: check if `Complete()` is called after processing
- **Root Causes**:
  - **Message loss**: `EnableExpress` enabled (messages kept in memory, lost on failover), consumer not calling `Complete()`, auto-delete on idle triggered
  - **Duplicate processing**: Consumer calling `Abandon()` or `Defer()` incorrectly, network issue causing duplicate delivery (at-least-once semantics)
  - **Message expiration**: TTL too short, messages expiring before processing
- **Resolution**: Disable `EnableExpress` for critical messages, ensure consumer calls `Complete()`, implement idempotent processing, extend TTL
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

## Correlation Rules

### Change Correlation

If anomaly start is within 30 minutes after an Activity Log event, increase confidence for that event as a cause.

High-risk change categories:
- key regeneration;
- namespace SKU/scale change;
- queue/topic config update (TTL, delivery count, partitioning);
- firewall/private endpoint update;
- geo-DR failover;
- app deployment reported by user.

### Dependency Correlation

If `OutgoingMessages` drops but producers are sending, correlate with consumer-side events (deployment, scaling, network changes). Service Bus alone cannot prove consumer-side issues; ask for consumer logs or delegate to `azure-vm-ops`, `azure-aks-ops`, or `azure-appservice-ops` based on consumer type.

### Network Correlation

If server metrics are normal but client errors rise, prioritize DNS, firewall, TLS, route, and private endpoint checks over namespace scaling.

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
| Safe | read metrics, show config, list queues/topics/subscriptions, query Activity Log | execute directly |
| Low | enable additional diagnostic collection when non-disruptive | ask if cost/noise impact unclear |
| Medium | modify TTL/delivery count/filter rules, scale Premium namespace up | require confirmation and rollback note |
| High | delete namespace/queue/topic/subscription, purge DLQ, regenerate keys | require explicit confirmation; use GCL |

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
- DLQ depth metrics alone cannot identify dead-letter reason; client-side message inspection is required for `deadLetterReason` / `deadLetterErrorDescription`.

## Cross-Skill Integration
- **azure-monitor-ops**: 诊断日志、Activity Log 深度审计、KQL 查询委托
- **azure-aks-ops**: 消费者应用部署在 AKS 时的容器日志、pod 健康检查
- **azure-appservice-ops**: 消费者应用部署在 App Service 时的应用日志
- **azure-vm-ops**: 消费者应用部署在 VM 时的系统日志、进程监控
- **标准诊断路径**: 参考 `docs/cross-skill-rca-schema.md` 的跨服务根因分析链
