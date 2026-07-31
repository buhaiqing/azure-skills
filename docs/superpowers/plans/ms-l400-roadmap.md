# Microsoft Level 400 Capable — Roadmap (azure-skills)

> Date: 2026-08-01
> Status: **Implemented** (Waves 0–4)
> Baseline: [ms-agentic-maturity-baseline.md](../reports/ms-agentic-maturity-baseline.md)

## Goal

Deliver **Microsoft Level 400 Capable (repository capability)** so adopters can operate agents with enterprise-grade tech foundations, risk-tiered governance, and measurable value — without claiming customer Organization & Culture = 400.

## DoD (all required)

1. ≥8 core skills have live canary report (not mock-only)
2. L4 metrics writable/queryable via Azure Monitor path
3. CI gates: heal-policy validate + mock suite
4. R0/R1/R2 risk tiers drive auto-heal / GCL / human confirm
5. At least one `value_report` artifact
6. Federated governance + RAI checks in governance-review
7. Wording: distinguish Gartner L4 Certified vs Microsoft L400 Capable (repo)

## Out of scope (Level 500 / Gartner L5)

- Unattended always-on autonomy across all subscriptions
- Predictive compliance
- Self-evolving multi-agent platform

## Waves

| Wave | Focus | Key artifacts |
|------|-------|---------------|
| 0 | Baseline | `ms-agentic-maturity-baseline.md` |
| 1 | Technology | live canary, Monitor, CI, eval weekly |
| 2 | Governance | `risk_tiers.json`, `watch_and_heal.py`, RAI, federation doc |
| 3 | Business/Strategy | `value_report.py`, human-agent playbook |
| 4 | Enablement | adoption tiers, user-guide, README claim |
