# Success Metrics

Key performance indicators for the CoE, aligned with `governance_dashboard.py` and `health_dashboard.py`.

## Primary KPIs

| Metric | Target | Description |
|--------|--------|-------------|
| Safety Pass Rate | **≥ 100%** | Percentage of agent executions that passed all live canary safety checks |
| Auto-Heal Success Rate | **≥ 85%** | Percentage of auto-remediation attempts that resolved the incident without human intervention |
| Live Canary Coverage | **≥ 80%** | Share of skill invocations covered by at least one live canary check |
| Escalation Rate | **≤ 15%** | Percentage of incidents auto-escalated to human on-call |
| MTTR Delta | **≤ 14 min** | Difference in mean time to resolve between auto-healed and manually-resolved incidents (auto must be faster) |

## Secondary KPIs

| Metric | Target | Description |
|--------|--------|-------------|
| Skill Deployment Frequency | ≥ 3/week | New or updated skills deployed to production |
| Change Failure Rate | ≤ 5% | Percentage of skill deployments requiring rollback |
| R2 Approval SLA | < 4h | Time from R2 approval request to decision |
| Canary Flakiness Rate | < 2% | False-fail rate across all live canary runs |

## Dashboard Alignment

All metrics above are exposed in:

- **`governance_dashboard.py`** — Safety Pass Rate, Escalation Rate, R2 Approval SLA, MTTR Delta
- **`health_dashboard.py`** — Live Canary Coverage, Auto-Heal Success Rate, Canary Flakiness Rate

Update these targets when organizational risk appetite changes. Any breach of a primary KPI triggers an automatic alert to the Platform Owner and AI Champion.
