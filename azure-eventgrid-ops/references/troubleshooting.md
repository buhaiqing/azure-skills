# Azure Event Grid Troubleshooting and RCA

## Method: Evidence Before Conclusion

Do not start with a fix. Collect evidence in this order:

1. Confirm subscription, Resource Group, topic/system topic/domain name, and provisioning state.
2. Build incident timeline: symptom start, event-subscription creates/deletes, key rotations, filter changes, source-resource changes (for system topics).
3. Inspect event-subscription delivery attributes (`get_delivery_attributes`) for the failing subscription — returns static/dynamic HTTP header attribute mappings for the subscription, not delivery counters.
4. Inspect dead-letter destination container if configured; identify event shape and handler response codes.
5. Query Activity Log for the topic / system topic / domain configuration changes.
6. Check Event Grid metrics for the affected resource (`PublishFailedEvents`, `DeliveryFailedEvents`, `DeadLetteredEvents`, `MatchedEvents`, `DroppedEvents`).
7. Verify handler endpoint health from handler-side logs (HTTP 5xx / 4xx / TLS / DNS).
8. Rank root-cause candidates by evidence and confidence.
9. Separate safe diagnostics from remediation needing confirmation.

## Symptom Index

| Symptom | First Evidence | Likely Area |
|---------|----------------|-------------|
| Events not arriving at handler | `MatchedEvents > 0` but `DeliveryFailedEvents > 0`; handler 5xx | handler availability, network, TLS, AAD auth on handler |
| Handler returns `ValidationFailed` once at creation | `validationCode` in handler request body, handler did not echo it back | webhook validation handshake; only the `validationCode` query / body handshake must succeed |
| Dead-letter container growing | `DeadLetteredEvents` metric rising, blob storage container shows `deadletter` blobs | handler returns non-retryable code (e.g. 400), or retries exhausted |
| Filter does not match any events | `MatchedEvents = 0`, `DroppedEvents` rising | `subjectBeginsWith` / `eventTypeIncluded` mismatch with actual events |
| Publish call returns 401 | topic access key wrong or revoked | key rotation gap; check `az eventgrid topic key list` |
| Publish call returns 403 / AuthorizationFailed | publisher RBAC missing `EventGrid Data Sender` or AAD token absent | RBAC; delegate to `azure-audit-ops` for role assignment |
| Publish call returns 413 | event payload > 1 MB | schema size limit; split or compress |
| Publish call returns 429 | per-topic publish rate exceeded | throttle backoff, or scale across topics |
| Subscription create fails with quota error | `ResourceQuotaExceeded` | request quota increase or consolidate subscriptions |
| System Topic disappeared after deleting source resource | source resource deleted → system topic auto-deleted | expected; recreate source and system topic together |
| CloudEvents handler rejects Event Grid Schema | handler expects `ce-` headers but receives Event Grid envelope | use `eventDeliverySchema: CloudEventSchemaV1_0` at subscription create |

## Triage Commands

```bash
# Topic state and provisioning
az eventgrid topic show \
  --name "{{user.topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,state:properties.provisioningState,endpoint:properties.endpoint,input_schema:properties.inputSchema}" \
  --output json

# System Topic state
az eventgrid system-topic show \
  --name "{{user.system_topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,state:properties.provisioningState,source:properties.source,topic_type:properties.topicType}" \
  --output json

# Event subscription state
az eventgrid event-subscription show \
  --name "{{user.event_subscription_name}}" \
  --source-resource-id "{{output.topic_id}}" \
  --query "{id:id,state:properties.provisioningState,destination:properties.destination,filter:properties.filter,retry:properties.retryPolicy,deadletter:properties.deadLetterWithResourceIdentity}" \
  --output json

# Event Grid metrics — delivery counters
az monitor metrics list \
  --resource "{{output.topic_id}}" \
  --metric "PublishFailedEvents,DeliveryFailedEvents,DeadLetteredEvents,MatchedEvents,DroppedEvents" \
  --interval PT1M \
  --aggregation Total \
  --output json

# Activity Log — config changes
az monitor activity-log list \
  --resource-group "{{user.resource_group}}" \
  --resource-id "{{output.topic_id}}" \
  --offset "{{user.analysis_window}}" \
  --output json
```

If a metric name fails, run `az monitor metrics list-definitions --resource "{{output.topic_id}}" --output json` and retry with verified names.

## Root Cause Rules

| Rule | Evidence Pattern | Confidence |
|------|------------------|------------|
| Filter mismatch | `MatchedEvents = 0`, `DroppedEvents` high; handler never called | High if `subjectBeginsWith` or `includedEventTypes` does not match observed event `subject` / `eventType` |
| Handler 5xx | `DeliveryFailedEvents` rising; handler logs show 500/502/503 | High |
| Handler 4xx (non-retryable) | `DeadLetteredEvents` rising after one failed attempt; handler returns 400 | High |
| Validation handshake failed | `Microsoft.EventGrid.SubscriptionValidationEvent` event delivered but handler returns 200 without echoing `validationCode` | High |
| Network / DNS to private endpoint | handler intermittent; metric shows delivery succeed/fail pattern | Medium; needs DNS resolution evidence |
| Topic access key rotation gap | publisher 401 after Activity Log `regenerate key` event | High |
| System topic tied to deleted source | system topic no longer exists after source resource deleted | High (expected behavior) |
| Quota exceeded | `ResourceQuotaExceeded` error on subscription/topic create | High |
| Schema mismatch | CloudEvents handler receives Event Grid envelope | High if `eventDeliverySchema` not set to `CloudEventSchemaV1_0` |
| Dead-letter destination missing | `deadletter` block set but storage account / container invalid; events never delivered and never dead-lettered | Medium; verify storage account existence and SAS validity |

## Correlation Playbooks

### Delivery Failures

1. Identify failing subscription via metrics (e.g. `DeliveryFailedEvents`, `DeadLetteredEvents`) or dead-letter inspection.
2. Inspect handler endpoint availability (DNS, TLS, HTTP probe from same VNet if private endpoint in use).
3. Inspect Activity Log for subscription or destination changes around incident start.
4. Inspect handler-side logs for returned status codes.

Safe actions:
- gather delivery metrics and Activity Log;
- list subscriptions on the topic;
- show subscription filter and retry policy.

Requires confirmation:
- delete failing subscription;
- modify filter (changing `subjectBeginsWith` changes which events flow);
- increase retry attempts or TTL;
- set dead-letter destination.

### Filter Mismatch

1. Compare `includedEventTypes` against actual event types emitted by source (use `az eventgrid topic list-event-types` for topic event type catalog).
2. Compare `subjectBeginsWith` / `subjectEndsWith` against the `subject` field of an example event (capture from handler logs or use test event).
3. Check `advancedFilters` JSON-path expressions.

Safe actions:
- list subscription filters;
- list event types for the topic;
- show one example event from handler logs.

Requires confirmation:
- update subscription filter;
- delete and recreate subscription.

### Dead-Letter Inspection

1. Identify dead-letter storage container (SAS-protected).
2. List blobs in the container; group by `eventType` and handler response code (encoded in blob metadata if dead-letter SDK used).
3. Inspect handler-side root cause for each non-retryable code.

Safe actions:
- list blobs in dead-letter container;
- read first ~10 dead-letter blobs for shape;
- report frequency and root cause distribution.

Requires confirmation:
- replay a subset of dead-letter events (operator decision required);
- delete dead-letter blobs after retention period.

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
Evidence: <metrics, delivery attributes, config, commands>
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
- handler application logs are required but unavailable;
- dead-letter replay is requested for production events;
- quota increase is needed and quota tooling is non-responsive.