# AIOps — Azure Monitor RCA Rules

> AIOps-driven root cause analysis for monitoring, alerting, diagnostics, and cross-service observability.

## Detection Signals

| Signal | Source | Description |
|--------|--------|-------------|
| metric_anomaly | `az monitor metrics list` | Metric deviates from rolling baseline > 3σ |
| alert_firing | `az monitor alert rule list` | Alert rule in fired state |
| log_error_spike | Log Analytics query | Error count spike > 5x baseline in 5min window |
| diag_missing | `az monitor diagnostic-setting list` | Resource missing diagnostic settings |
| cost_anomaly | Delegation to `azure-cost-ops` | Cost spike detected (cross-skill signal) |

## RCA Rules

### Rule: Metric Anomaly Root Cause
```
trigger: metric_anomaly detected (any metric)
flow:
  1. Determine affected resource: az monitor metrics list --resource <id> --metric <metric>
  2. Check Activity Log for recent resource changes (last 1h):
     az monitor activity-log list --correlation-id <id>
  3. Correlate with dependent resources:
     - If VM metric → check Azure VM ops for status
     - If App Gateway metric → check azure-appgateway-ops for backend health
     - If SQL metric → check azure-sqldb-ops for DTU/query performance
  4. Generate RCA report with timeline
output: {
  "resource": "<resource_id>",
  "metric": "<metric_name>",
  "anomaly_magnitude": "<deviation_pct>",
  "correlated_events": ["activity_log_entries"],
  "probable_cause": "<analysis>"
}
```

### Rule: Alert-Driven Auto-Healing
```
trigger: alert_firing with severity 0-2
flow:
  1. Parse alert context: resource_id, metric, threshold, current value
  2. Map to responsible skill:
     - VM-related → delegate to azure-vm-ops AIOps
     - AKS-related → delegate to azure-aks-ops AIOps
     - Network-related → delegate to azure-loadbalancer-ops AIOps
     - Cost-related → delegate to azure-cost-ops AIOps
  3. If healing action is available and safe (non-destructive):
     - Call auto_feedback_loop.py with the healing strategy
     - Monitor result for 5 minutes
  4. If healing fails or action is destructive → escalate to human
  5. Log the entire healing attempt to Activity Log
```

### Rule: Diagnostic Coverage Check
```
trigger: weekly scan or on-demand
flow:
  1. List all resources in subscription: az resource list
  2. For each resource, check diagnostic settings: az monitor diagnostic-setting list
  3. Identify resources missing diagnostics
  4. For critical resources (VM, AKS, SQL, App Gateway), auto-recommend enabling
  5. Generate diagnostic coverage report
```

### Rule: Cost-Aware Alert Correlation
```
trigger: cost_anomaly signal from azure-cost-ops
flow:
  1. Accept cost anomaly event (resource, cost_increase_pct, timeframe)
  2. Query metrics for the affected resource in the same timeframe:
     az monitor metrics list --resource <id> --interval PT1H
  3. Check if metric changes correlate with cost changes:
     - CPU/Memory scale-up → cost increase expected
     - No metric change but cost increased → investigate billing tier change
  4. Generate combined report: cost + performance impact
```

## Integration with Self-Healing Loop

The L4 auto-feedback loop (`auto_feedback_loop.py`) integrates with Monitor as follows:

| Stage | Monitor Role |
|-------|-------------|
| Observe | Query metrics + Activity Log via Monitor |
| Diff | Compare observed metrics against alert thresholds |
| Heal | If safe action available, execute via `auto_feedback_loop.py` with the responsible skill |
| Escalate | If healing fails, generate diagnostic context with Monitor data |

## Escalation Rules

| Condition | Action | Priority |
|-----------|--------|----------|
| Metric anomaly + no recent Activity Log events | Investigate resource health directly | P1 |
| Alert firing + no healing action available | Escalate with full diagnostic context | P0 |
| Diagnostic coverage < 80% for critical resources | Generate enablement plan | P2 |
| Cross-service anomaly detected | Trigger cross-skill RCA flow | P1 |

## Cross-Skill Integration

See `docs/cross-skill-rca-schema.md` for standard diagnostic paths and cross-service root cause analysis chains.

When this skill detects an anomaly that may involve other services:
- Delegate to `azure-monitor-ops` for metric correlation and Activity Log investigation
- Follow the standard diagnostic path defined in `docs/cross-skill-rca-schema.md`