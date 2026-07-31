# Federated Governance — azure-skills

MS Level 400: central standards with delegated approvals for low-risk agents.

## Approval matrix

| Tier | Ops class | Who can approve auto-run | GCL | Auto-heal |
|------|-----------|--------------------------|-----|-----------|
| **R0** | Read-only (`list`/`show`/`query`) | Team lead / on-call | Optional | Yes |
| **R1** | Mutable reversible (`create`/`update`/`start`) | Service owner | Required | Yes (max 2) |
| **R2** | Destructive (`delete`/`purge`/`stop`) | Platform + security (two-party) | Required, max_iter=2 | **No** — human only |

Source of truth: [`scripts/risk_tiers.json`](../scripts/risk_tiers.json).

## Central standards (do not fork)

- Variable convention: `{{env.*}}` / `{{user.*}}` / `{{output.*}}`
- Dual-path: Azure CLI primary, SDK fallback
- Destructive human confirmation (AGENTS.md + skill Quality Gate)
- Trace persistence under `audit-results/`
- Heal policies validated by `scripts/self_healing/validate.py` (CI)

## Delegated (federated) decisions

Adopters may without changing core repo:

1. Map which Azure subscriptions are sandbox / team / enterprise ([adoption-tiers](./adoption-tiers.md))
2. Choose LLM Critic provider (`CRITIC_PROVIDER`) vs rule-based
3. Tighten R1 → require human confirm for production RGs (wrap CLI with policy)
4. Route escalations to PagerDuty/Teams (post-process `watch-and-heal-last.json`)

## AI Council rhythm (suggested)

| Cadence | Agenda |
|---------|--------|
| Weekly | `eval_weekly.py` output + heal failure review |
| Monthly | `value_report.py` business KPIs + retire unused skills |
| Quarterly | Risk-tier audit; RAI checklist spot-check on 3 skills |

## Related

- [human-agent-ops-playbook](./human-agent-ops-playbook.md)
- [governance-review](../azure-skill-generator/references/governance-review.md)
