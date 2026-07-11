# Azure Service Bus AIOps Analysis

## Purpose

AIOps in this skill means metric anomaly detection, evidence correlation, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Inputs

| Input | Source |
|-------|--------|
| Resource state | `az servicebus namespace show`, `az servicebus queue show`, `az servicebus topic show` |
| Metrics | Azure Monitor metrics |
| Activity timeline | Activity Log, delegate deep audit to `azure-audit-ops` |
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

If `OutgoingMessages` drops but producers are sending, correlate with consumer-side events (deployment, scaling, network changes). Service Bus alone cannot prove consumer-side issues; ask for consumer logs or delegate to the relevant app support skill.

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
