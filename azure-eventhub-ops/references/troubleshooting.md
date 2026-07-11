# Azure Event Hubs Troubleshooting and RCA

## Method: Evidence Before Conclusion

Do not start with a fix. Collect evidence in this order:

1. Confirm subscription, Resource Group, namespace name, SKU, Location, and provisioning state.
2. Build incident timeline: symptom start, deployments, namespace updates, key rotation, Capture toggle, firewall/private endpoint changes.
3. Query Event Hubs metrics for `{{user.analysis_window}}` and compare with a previous healthy window.
4. Check Activity Log for configuration changes.
5. Inspect networking: firewall rules, private endpoint state, DNS resolution path.
6. Inspect Capture backlog if Capture is enabled.
7. Rank root-cause candidates by evidence and confidence.
8. Separate safe diagnostics from remediation needing confirmation.

## Symptom Index

| Symptom | First Evidence | Likely Area |
|---------|----------------|-------------|
| Throttling / 429 errors | `ThrottledRequests` rising, `IncomingBytes` near TU/PU limit | capacity, auto-inflate, partition skew |
| High consumer lag | `ConsumerLag` metric, consumer group falling behind | consumer throughput, partition count, processing speed |
| Partition skew | one partition's lag much higher than others | partition key design, hot partition |
| Capture falling behind | `CaptureBacklog` growing, Capture not writing to Blob | storage account, Capture config, IAM |
| Connection failures | `ActiveConnections` drop, `UserErrors` rising | firewall, private endpoint, auth keys, Kafka config |
| Server errors | `ServerErrors` rising, 5xx | Azure service issue, quota exceeded |
| Message throughput drop | `IncomingMessages` / `OutgoingMessages` drop | producer/consumer-side issue, namespace state |
| Authorization failures | `UserErrors` with auth errors | stale keys, RBAC change, SAS token expiry |

## Triage Commands

```bash
az eventhubs namespace show \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,state:properties.provisioningState,sku:sku.name,tu:sku.capacity,endpoint:properties.serviceBusEndpoint}" \
  --output json

az eventhubs eventhub list \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az monitor metrics list \
  --resource "{{output.namespace_id}}" \
  --metric "ThrottledRequests,IncomingBytes,OutgoingBytes,IncomingMessages,OutgoingMessages,SuccessfulRequests,ServerErrors,UserErrors,ActiveConnections,CaptureBacklog" \
  --interval PT1M \
  --aggregation Average,Maximum,Total \
  --output json

az monitor activity-log list \
  --resource-group "{{user.resource_group}}" \
  --resource-id "{{output.namespace_id}}" \
  --offset "{{user.analysis_window}}" \
  --output json
```

If a metric name fails, run `az monitor metrics list-definitions --resource "{{output.namespace_id}}" --output json` and retry with verified names.

## Root Cause Rules

| Rule | Evidence Pattern | Confidence |
|------|------------------|------------|
| TU/PU capacity exhaustion | `ThrottledRequests` + `IncomingBytes` near TU/PU limit, no auto-inflate or auto-inflate maxed | High |
| Partition skew (hot partition) | one partition lag much higher, `IncomingBytes` unbalanced across partitions | Medium; High if partition key pattern identified |
| Consumer processing slow | `ConsumerLag` rising, consumer instance count flat | Medium; needs consumer-side evidence |
| Auto-inflate misconfigured | throttling present + auto-inflate disabled or max TU too low | High |
| Capture storage failure | `CaptureBacklog` rising + storage account inaccessible | High |
| Private endpoint misrouting | connection failures + private endpoint state not Approved or DNS wrong | High |
| Firewall deny | connection failures + public endpoint + client IP outside allowlist | High |
| Stale auth key | auth failures start after key rotation event | High |
| Azure service issue | `ServerErrors` rising across resources + correlation IDs | Low until Azure status/correlation evidence |
| Consumer group not created | consumer lag only on `$Default` with multiple consumer apps | Medium |

## Correlation Playbooks

### Throughput Throttling

1. Identify throttling window from user or `ThrottledRequests` metric.
2. Compare `IncomingBytes` against namespace TU/PU limit (Standard: 1 MB/s per TU; Premium: check PU specs).
3. Check auto-inflate setting and current TU/PU count.
4. Check `CaptureBacklog` — Capture can consume throughput if enabled.
5. Check per-partition distribution if partition-level metrics available.

Safe actions:
- gather metrics and Activity Log;
- inspect namespace config (SKU, TU/PU, auto-inflate);
- recommend auto-inflate or scale-up plan.

Requires confirmation:
- increase TU/PU;
- enable auto-inflate;
- scale up SKU (Standard→Premium).

### Consumer Lag

1. Identify `ConsumerLag` per partition.
2. Check consumer group configuration and consumer instance count.
3. Correlate with consumer app deployment or processing logic changes.
4. If single partition lag is much higher, classify as partition skew.

Safe actions:
- gather consumer lag metrics;
- list consumer groups;
- report lag distribution across partitions.

Requires confirmation:
- increase partition count (not possible — create new event hub with more partitions);
- scale consumer group instances.

### Capture Failure

1. Check `CaptureBacklog` metric.
2. Verify storage account exists and container is accessible.
3. Check Capture IAM (storage account role assignment).
4. Check Activity Log for storage account or Capture config changes.

Safe actions:
- check Capture config on event hub;
- verify storage account exists and RBAC;
- list Capture errors in metrics.

Requires confirmation:
- re-enable Capture;
- update storage account/container;
- assign storage IAM role.

## Decision Matrix

| Finding | Action |
|---------|--------|
| Strong evidence, safe diagnostic | Execute and report |
| Strong evidence, low-risk config read | Execute and report |
| Medium evidence, remediation is disruptive | Recommend approval-gated action; do not execute |
| Low evidence | Collect more logs/metrics or escalate |
| User asks to skip confirmation | Refuse and HALT |

## RCA Report Template

```text
Symptom: <what user observed>
Timeline: <start, peak, recent changes>
Evidence: <metrics, logs, config, commands>
Most likely root causes:
1. <cause> — Confidence: High|Medium|Low — Evidence: <evidence>
2. <cause> — Confidence: High|Medium|Low — Evidence: <evidence>
Safe next actions:
- <read-only diagnostic or app-owner check>
Actions requiring confirmation:
- <operation, expected impact, rollback/mitigation>
Escalation criteria:
- <when to involve Azure Support/app team/network team>
```

## Escalation Criteria

Escalate when:
- Azure control plane returns repeated 5xx with correlation IDs;
- private endpoint/DNS evidence requires network owner access;
- consumer/client logs are required but unavailable;
- key rotation or namespace deletion is requested for production;
- multiple dependent systems impacted and Event Hubs evidence is inconclusive.
