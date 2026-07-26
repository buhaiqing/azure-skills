# AIOps — Cost Management RCA Rules

> AIOps-driven root cause analysis for cost anomalies, budget overruns, reservation optimization, and tag compliance.

## Detection Signals

| Signal | Source | Description |
|--------|--------|-------------|
| cost_spike | `az costmanagement query` | Month-over-month cost increase > 20% |
| budget_consumption | `az consumption budget show` | Budget consumed > 80% before mid-cycle |
| ri_utilization | `az reservations reservation list` | Reserved instance utilization < 80% for 30 days |
| untagged_resources | `az resource list --query "[?tags==null]"` | Resources without mandatory cost tags |

## RCA Rules

### Rule: Cost Spike Detection
```
trigger: current_month_cost > previous_month_cost * 1.2
flow:
  1. Query cost by service: az costmanagement query --scope ... --timeframe MonthToDate
  2. Identify top-cost-increased service(s)
  3. For each service, query by resource to find new or scaled-up resources
  4. Check Activity Log for correlated resource creation events
  5. Attribute cost increase to team/resource group (via tags)
output: {
  "root_cause": "service/resource/operation that caused the spike",
  "cost_increase_pct": <float>,
  "affected_resources": ["..."],
  "recommendation": "right-size / stop / tag"
}
```

### Rule: Budget Overrun Prevention
```
trigger: budget_consumption > 0.8 (before mid-cycle)
flow:
  1. Identify top-spending resources in current period
  2. Check for anomalous spending patterns (new deployments, traffic spikes)
  3. Optional: trigger budget alert via az monitor metrics alert
  4. If forecast shows >100% consumption, recommend budget increase or cost optimization
```

### Rule: RI / Savings Plan Optimization
```
trigger: ri_utilization < 0.8 for 30 consecutive days
flow:
  1. List all reservations: az reservations reservation list
  2. Calculate per-reservation utilization
  3. For under-utilized RIs:
     a. Check if size flexibility can improve utilization
     b. Recommend RI exchange (az reservations reservation exchange)
     c. If exchange not viable, recommend partial refund
  4. Escalate to human for confirmation before any modification
```

### Rule: Tag Compliance Audit
```
trigger: monthly cost review or on-demand
flow:
  1. List resources without cost tags: az resource list --query "[?tags==null || tags.cost-center==null]"
  2. Calculate untagged cost share: total cost of untagged resources / total cost
  3. If untagged share > 10%, recommend tagging with cost-center, environment, owner
  4. Generate report for team leads
```

## Cost-Aware Alerting (Integration with azure-monitor-ops)

When AIOps detects a cost anomaly, it SHOULD:
1. Create or update a budget alert (via `azure-monitor-ops` delegation)
2. Log the finding to Activity Log for audit trail
3. Optionally trigger an Action Group notification (email/webhook)

## Escalation Rules

| Condition | Action | Priority |
|-----------|--------|----------|
| Cost spike > 50% MoM | Immediate escalation + Activity Log investigation | P0 |
| Budget > 90% with >7 days remaining | Create budget alert + notify team | P1 |
| RI utilization < 60% | Recommend RI exchange with financial impact estimate | P1 |
| Untagged cost share > 20% | Generate report for FinOps team | P2 |

## Cross-Skill Integration

See `docs/cross-skill-rca-schema.md` for standard diagnostic paths and cross-service root cause analysis chains.

When this skill detects an anomaly that may involve other services:
- Delegate to `azure-monitor-ops` for metric correlation and Activity Log investigation
- Follow the standard diagnostic path defined in `docs/cross-skill-rca-schema.md`