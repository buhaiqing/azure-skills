# AIOps — Application Gateway RCA Rules

> AIOps-driven root cause analysis for Azure Application Gateway anomalies.

## Detection Signals

| Signal | Source | Description |
|--------|--------|-------------|
| backend_unhealthy | `az network application-gateway show-backend-health` | Backend pool health check failing |
| http_502 | `az monitor metrics list` --metric "Failed Requests" | 502 errors from backend |
| waf_blocked | `az monitor diagnostic-setting list` + Log Analytics | WAF blocking legitimate traffic |
| backend_timeout | `az monitor metrics list` --metric "Backend Connect Time" | Backend response time > 30s |

## RCA Rules

### Rule: Backend Health Failure
```
trigger: backend_unhealthy
flow:
  1. Show backend health: az network application-gateway show-backend-health --name <gw> --resource-group <rg>
  2. Check backend pool members' status
  3. If all unhealthy: check backend service (VM/App Service/AKS) independently
  4. If some unhealthy: check load distribution and health probe configuration
  5. Verify health probe path and interval match backend readiness
```

### Rule: 502 Error Diagnosis
```
trigger: http_502
flow:
  1. Check backend health: show-backend-health
  2. Check backend timeout settings: az network application-gateway http-settings show --name <settings>
  3. If timeout < 30s: recommend increasing request_timeout
  4. Check backend server logs for errors
```

### Rule: WAF False Positive Investigation
```
trigger: waf_blocked
flow:
  1. Check WAF logs: az monitor diagnostic-setting list --resource <gw_id>
  2. Identify blocked request pattern (URI, IP, rule ID)
  3. If legitimate traffic being blocked: create WAF exclusion for specific rule
  4. If attack: recommend blocking source IP in NSG
```

### Rule: Backend Timeout Resolution
```
trigger: backend_timeout
flow:
  1. Check backend response time: az monitor metrics list --resource <gw_id> --metric "Backend Response Time"
  2. Check backend server load (delegate to `azure-vm-ops`, `azure-aks-ops`, or `azure-appservice-ops` based on backend type)
  3. If backend overloaded: recommend scaling
  4. If network latency: check VNet peering / ExpressRoute

## Cross-Skill Integration

See `docs/cross-skill-rca-schema.md` for standard diagnostic paths and cross-service root cause analysis chains.

When this skill detects an anomaly that may involve other services:
- Delegate to `azure-monitor-ops` for metric correlation and Activity Log investigation
- Follow the standard diagnostic path defined in `docs/cross-skill-rca-schema.md`
```