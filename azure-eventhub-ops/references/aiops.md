# Azure Event Hubs AIOps Analysis

## Purpose

AIOps in this skill means metric anomaly detection, evidence correlation, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Inputs

| Input | Source |
|-------|--------|
| Resource state | `az eventhubs namespace show`, `az eventhubs eventhub show` |
| Metrics | Azure Monitor metrics |
| Activity timeline | Activity Log, delegate deep audit to `azure-audit-ops` |
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
