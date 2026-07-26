# AIOps — API Management RCA Rules

> AIOps-driven root cause analysis for Azure API Management anomalies.

## Detection Signals

| Signal | Source | Description |
|--------|--------|-------------|
| api_throttled | `az monitor metrics list` --metric "ThrottledRequests" | API calls being rate-limited |
| backend_timeout | `az monitor metrics list` --metric "BackendDuration" | Backend response > timeout |
| subscription_expired | `az apim subscription list` --query "[?state=='expired']" | API subscription keys expired |
| gateway_error | `az monitor metrics list` --metric "FailedRequests" | Gateway returns 5xx |

## RCA Rules

### Rule: API Throttling Diagnosis
```
trigger: api_throttled
flow:
  1. Check rate limit policy: az apim api policy list --service <apim> --api-id <api>
  2. Check current call rate: az monitor metrics list --resource <apim_id> --metric "Requests" --interval PT1M
  3. If exceeding rate limit: recommend increasing limit or optimizing call frequency
  4. If no rate limit configured: check if Azure subscription-level limits apply
```

### Rule: Backend Timeout Resolution
```
trigger: backend_timeout
flow:
  1. Check backend configuration: az apim api show --service <apim> --api-id <api>
  2. Check backend service URL and timeout setting
  3. If backend slow: delegate to `azure-vm-ops`, `azure-appservice-ops`, or `azure-function-ops` based on backend type
  4. If timeout too low: recommend increasing backend timeout in API policy
```

### Rule: Subscription Key Expiry
```
trigger: subscription_expired
flow:
  1. List expired subscriptions: az apim subscription list --service <apim> --query "[?state=='expired']"
  2. For each expired subscription:
     - Check associated product and API
     - Identify owner (via tags or product scope)
  3. Recommend: regenerate key and notify API consumer
  4. For critical APIs: auto-renew with new key
```

### Rule: Gateway Error Investigation
```
trigger: gateway_error
flow:
  1. Check APIM metrics for error distribution: az monitor metrics list --resource <apim_id> --metric "FailedRequests"
  2. Check APIM logs for specific error codes
  3. Common causes:
     - Backend unavailable → check backend service health
     - Invalid certificate → check custom domain SSL
     - Policy error → validate API policies

## Cross-Skill Integration

See `docs/cross-skill-rca-schema.md` for standard diagnostic paths and cross-service root cause analysis chains.

When this skill detects an anomaly that may involve other services:
- Delegate to `azure-monitor-ops` for metric correlation and Activity Log investigation
- Follow the standard diagnostic path defined in `docs/cross-skill-rca-schema.md`
```