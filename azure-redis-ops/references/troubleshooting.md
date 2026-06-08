# Azure Redis Troubleshooting and RCA

## Method: Evidence Before Conclusion

Do not start with a fix. Collect evidence in this order:

1. Confirm subscription, Resource Group, resource name, SKU, Location, and provisioning state.
2. Build incident timeline: symptom start, deployments, scale/reboot/key rotation, firewall/private endpoint changes.
3. Query Redis metrics for `{{user.analysis_window}}` and compare with a previous healthy window.
4. Check Activity Log for configuration changes.
5. Inspect networking: firewall rules, private endpoint state, DNS resolution path.
6. Rank root-cause candidates by evidence and confidence.
7. Separate safe diagnostics from remediation needing confirmation.

## Symptom Index

| Symptom | First Evidence | Likely Area |
|---------|----------------|-------------|
| High latency / timeout | server load, ops/sec, bandwidth, client errors | load, slow commands, network |
| Memory pressure | used memory %, fragmentation, evictions | capacity, TTL, eviction policy |
| Evicted keys rising | evictedkeys + memory % | maxmemory pressure |
| Hit rate drop | cachehits/cachemisses | key expiry, cache warming, workload shift |
| Connected clients spike | connectedclients | client pool leak or surge |
| Bandwidth saturation | cacheRead/cacheWrite | large values or read amplification |
| Auth failures | client errors, key rotation events | stale keys, TLS/auth config |
| Private endpoint cannot connect | PE state, DNS, firewall | DNS/VNet/private link |
| After reboot failures | Activity Log + client errors | client reconnect/backoff problem |

## Triage Commands

```bash
az redis show \
  --name "{{user.redis_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,state:provisioningState,host:hostName,sku:sku,sslPort:sslPort,nonSsl:enableNonSslPort}" \
  --output json

az monitor metrics list \
  --resource "{{output.redis_id}}" \
  --metric "usedmemorypercentage,serverload,connectedclients,cachehits,cachemisses,evictedkeys,operationsPerSecond,cacheRead,cacheWrite" \
  --interval PT1M \
  --aggregation Average,Maximum,Total \
  --output json

az monitor activity-log list \
  --resource-group "{{user.resource_group}}" \
  --resource-id "{{output.redis_id}}" \
  --offset "{{user.analysis_window}}" \
  --output json
```

If a metric name fails, run `az monitor metrics list-definitions --resource "{{output.redis_id}}" --output json` and retry with verified names.

## Root Cause Rules

| Rule | Evidence Pattern | Confidence |
|------|------------------|------------|
| Hot key / slow command pressure | latency + high serverload + ops/sec spike, without memory spike | Medium; High if client logs show specific key/command |
| Memory capacity pressure | used memory high + evictedkeys rising | High |
| Eviction policy mismatch | evictions rising + TTL missing or noeviction/write errors | Medium |
| Client connection leak | connectedclients steadily grows while ops/sec flat | High if app deploy happened near start |
| Traffic surge | connectedclients + ops/sec + bandwidth rise together | Medium |
| Cache stampede / expiry storm | hit rate drops + backend DB load rises + cache misses spike | Medium; needs app/backend evidence |
| Large value/read amplification | bandwidth high + ops/sec normal + latency high | Medium |
| Stale key after rotation | auth failures start after regenerate-keys event | High |
| Private DNS issue | private endpoint approved but clients resolve public hostname or NXDOMAIN | High |
| Firewall deny | public endpoint used + client IP outside allowlist | High |
| Azure service issue | multiple resources affected + 5xx/control-plane events | Low until Azure status/correlation evidence |

## Correlation Playbooks

### Latency / Timeout

1. Identify latency window from user or metrics.
2. Compare serverload, ops/sec, connectedclients, cacheRead/cacheWrite.
3. Check Activity Log for reboot, scale, key regeneration, firewall/private endpoint change.
4. Ask user for client-side timeout/error samples if Azure metrics are inconclusive.
5. Report whether evidence points to load, network, auth, or client behavior.

Safe actions:
- gather metrics and Activity Log;
- inspect config and network state;
- suggest client retry/backoff review.

Requires confirmation:
- reboot;
- scale up/down;
- firewall changes;
- key regeneration.

### Memory Pressure / Evictions

1. Check used memory %, evictedkeys, cache hits/misses.
2. Check SKU/capacity and maxmemory policy.
3. Correlate with deployment or workload increase.
4. Identify whether eviction is expected, capacity exhaustion, or TTL/policy issue.

Safe actions:
- recommend key TTL audit;
- recommend large-key sampling by app/DBA team;
- recommend scale-up plan.

Requires confirmation:
- scale change;
- config update;
- purge/flush.

### Hit Rate Drop

1. Compute hit rate from hits/(hits+misses) over incident and baseline windows.
2. Check miss spike timing vs key expiration, deploy, data load, cache flush, or key namespace change.
3. Correlate with backend DB/API load if available.

Likely causes:
- cache warming failure;
- TTL too low;
- key naming/version change;
- cache stampede;
- data shape shift.

### Connectivity / Private Endpoint

1. Confirm Redis host, SSL port, TLS-only config.
2. List firewall rules and private endpoint connections.
3. Confirm private endpoint state is Approved.
4. Validate DNS path from client VNet. If not possible from agent environment, request user-run `nslookup` from affected subnet.
5. Check Activity Log for private endpoint, DNS zone, VNet link, and firewall changes.

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
- <when to involve Azure Support/app team/DBA/network team>
```

## Escalation Criteria

Escalate when:
- Azure control plane returns repeated 5xx with correlation IDs;
- private endpoint/DNS evidence requires network owner access;
- client logs are required but unavailable;
- data purge, reboot, or key rotation is requested for production;
- multiple dependent systems are impacted and Redis evidence is inconclusive.
