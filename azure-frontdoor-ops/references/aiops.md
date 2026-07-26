# AIOps — Front Door RCA Rules

> AIOps-driven root cause analysis for Azure Front Door anomalies.

## Detection Signals

| Signal | Source | Description |
|--------|--------|-------------|
| origin_unhealthy | `az afd endpoint show` / health probes | Origin marked unhealthy |
| cache_miss_high | `az monitor metrics list` --metric "CacheHitRate" | Cache hit rate < 50% |
| latency_spike | `az monitor metrics list` --metric "Latency" | P95 latency > 1s |
| waf_blocked | `az afd waf-policy list` | WAF blocking traffic |

## RCA Rules

### Rule: Origin Health Failure
```
trigger: origin_unhealthy
flow:
  1. Check origin configuration: az afd origin show --origin-group-name <group> --profile <profile> --resource-group <rg>
  2. Check origin health by region: az afd endpoint list --profile <profile>
  3. If private origin: check Private Link status
  4. If all origins unhealthy: check actual origin service (App Service / Storage / VM)
  5. If single region: check regional Azure health status
```

### Rule: Cache Performance Diagnosis
```
trigger: cache_miss_high
flow:
  1. Check caching rules: az afd route show --endpoint-name <ep> --profile <profile>
  2. Verify Cache-Control headers from origin (max-age, s-maxage)
  3. If no caching headers: recommend configuring on origin
  4. Check query string caching behavior: strip vs include
```

### Rule: Latency Investigation
```
trigger: latency_spike
flow:
  1. Check latency by region: az monitor metrics list --resource <fd_id> --metric "Latency" --dimension "Region"
  2. Check if origin in specific region is slow: compare regions
  3. If global latency: check CDN POP availability
  4. If single region high: check Azure regional health
```

### Rule: WAF Block Investigation
```
trigger: waf_blocked
flow:
  1. Check WAF policy: az afd waf-policy show --name <waf> --resource-group <rg>
  2. Check WAF logs for blocked request patterns
  3. If false positive: create custom rule exception
  4. If attack: recommend rate limiting rule

## Cross-Skill Integration

See `docs/cross-skill-rca-schema.md` for standard diagnostic paths and cross-service root cause analysis chains.

When this skill detects an anomaly that may involve other services:
- Delegate to `azure-monitor-ops` for metric correlation and Activity Log investigation
- Follow the standard diagnostic path defined in `docs/cross-skill-rca-schema.md`
```