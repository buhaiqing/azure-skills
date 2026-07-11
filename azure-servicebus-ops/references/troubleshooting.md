# Azure Service Bus Troubleshooting and RCA

## Method: Evidence Before Conclusion

Do not start with a fix. Collect evidence in this order:

1. Confirm subscription, Resource Group, namespace, queue/topic/subscription name, SKU, Location, and provisioning state.
2. Build incident timeline: symptom start, deployments, config changes, key rotation.
3. Query Service Bus metrics for `{{user.analysis_window}}` and compare with a previous healthy window.
4. Check Activity Log for configuration changes.
5. Inspect networking: firewall rules, private endpoint state, DNS resolution path.
6. Check DLQ depth and dead-letter reason for message-level issues.
7. Rank root-cause candidates by evidence and confidence.
8. Separate safe diagnostics from remediation needing confirmation.

## Symptom Index

| Symptom | First Evidence | Likely Area |
|---------|----------------|-------------|
| Dead-letter queue growing | `DeadletteredMessages` metric, DLQ depth query | Poison message, TTL expiry, delivery count exceeded |
| Message delay / high latency | `IncomingMessages` vs `OutgoingMessages` gap, latency metrics | Backlog, consumer lag, throttling, network |
| Quota exhausted | `ThrottledRequests` > 0, 429 errors | Namespace throughput unit, connection count, queue/topic count |
| Connection failures | `UserErrors`, client-side timeout logs | Auth, network, firewall, private endpoint |
| Messages not received | `OutgoingMessages` = 0 while `IncomingMessages` > 0 | Subscription filter mismatch, auto-forwarding loop, consumer offline |
| Duplicate messages | Consumer sees duplicates | Duplicate detection window too small, consumer ack lost |
| Slow consumer | `ActiveMessages` growing, consumer throughput flat | Consumer scaling, lock duration, processing time |
| Geo-DR failover issues | DR config state, `break_pairing` / `fail_over` history | Replication lag, manual failover not yet triggered |

## Triage Commands

```bash
az servicebus namespace show \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,state:provisioningState,sku:sku.name,location:location}" \
  --output json

az monitor metrics list \
  --resource "{{output.namespace_id}}" \
  --metric "IncomingMessages,OutgoingMessages,ActiveMessages,DeadletteredMessages,ThrottledRequests,ServerErrors,UserErrors" \
  --interval PT5M \
  --aggregation Total,Average,Maximum \
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
| Poison message loop | DLQ rising + `maxDeliveryCount` reached + message not processable | High |
| TTL misconfiguration | Messages expired before processing + `deadLetteringOnMessageExpiration` enabled | High |
| Consumer scale insufficient | `ActiveMessages` growing + consumer throughput flat | Medium |
| Quota/throttling pressure | `ThrottledRequests` > 0 + `ServerErrors` > 0 | High |
| Subscription filter mismatch | Messages sent to topic but `OutgoingMessages` = 0 on subscription | Medium |
| Auto-forwarding loop | Messages forwarded in cycle + no subscription consuming | Medium |
| Network/firewall issue | `UserErrors` + client timeout + no server-side errors | Medium |
| Geo-DR config not activated | DR state `PairingBroken` but no `fail_over` executed | High |
| Auth key rotation stale | `UserErrors` rise after key rotation event | High |
| Azure service issue | Multiple resources affected + `ServerErrors` + control-plane events | Low until Azure status evidence |

## Correlation Playbooks

### Dead-Letter Queue Growth

1. Query DLQ depth: check `DeadletteredMessages` metric trend.
2. Identify dead-letter reason: requires client-side inspection (message `deadLetterReason`, `deadLetterErrorDescription`).
3. Check Activity Log for config changes: TTL, delivery count, filter rules.
4. Common causes:
   - **Poison messages**: Increase `maxDeliveryCount` or fix consumer to handle bad messages
   - **TTL expiry**: Verify `defaultMessageTimeToLive` and `deadLetteringOnMessageExpiration`
   - **Filter mismatch**: Check subscription rules and message properties
5. Safe actions: read metrics, show config, query Activity Log.
6. Requires confirmation: change TTL, delivery count, filter rules; purge DLQ.

### Message Delay / Backlog

1. Compare `IncomingMessages` vs `OutgoingMessages` trend.
2. Check consumer-side lock duration and processing time.
3. Evaluate namespace throughput units (Premium) or partition count.
4. Check `ThrottledRequests` and `ServerErrors`.
5. Safe actions: gather metrics, check consumer logs.
6. Requires confirmation: scale namespace (Premium), add partitions (requires new namespace).

### Quota Exhaustion

1. Identify throttled operations from `ThrottledRequests` and 429 error details.
2. Check namespace limits: throughput units (Premium), queue/topic count, connection count.
3. Check queue/topic sizing: max size, partition count.
4. Safe actions: read current usage and limits.
5. Requires confirmation: scale up namespace, request quota increase via Azure Support.

### Connectivity Issues

1. Confirm namespace hostname resolves and is reachable from agent environment.
2. List firewall rules, IP ACLs, and private endpoint connections.
3. Validate private endpoint state (Approved) and DNS zone configuration.
4. Check Activity Log for private endpoint, DNS zone, VNet link, and firewall changes.
5. Safe actions: show namespace network config, list firewall rules, check private endpoint state.
6. Requires confirmation: modify firewall rules, approve/reject private endpoint connections.

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
- client-side message content inspection is required but unavailable;
- data purge, key rotation, or namespace delete is requested for production;
- multiple dependent systems impacted and Service Bus evidence is inconclusive.
