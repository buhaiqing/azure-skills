# Week One Checklist

Day-by-day execution plan for the AI Champion and Platform Owner during the first week of CoE adoption.

## Day 1 — Azure Credentials + CI Configuration

| Task | Owner | DoD | Est. Hours |
|------|-------|-----|------------|
| Configure Azure credentials in CI secrets | Platform Owner | `python3 scripts/live_canary.py --env=live` runs successfully | 2h |

**Verification:** Run `python3 scripts/live_canary.py --env=live` — must exit 0 with no ERROR lines.

---

## Day 2 — Core Skill Validation

| Task | Owner | DoD | Est. Hours |
|------|-------|-----|------------|
| Execute full live canary suite | AI Champion | All 15 live canary checks pass | 2h |

**Verification:** Output shows `15/15 passed` with zero failures.

---

## Day 3 — Governance Configuration

| Task | Owner | DoD | Est. Hours |
|------|-------|-----|------------|
| Adapt `risk_tiers.json` to org risk appetite | Platform Owner | `risk_tiers.json` reflects org thresholds | 2h |
| Configure escalation webhook | Platform Owner | Webhook fires on `risk_tier == CRITICAL` event | 1h |

**Verification:** Trigger a CRITICAL-tier event and confirm the webhook receives a payload within 30 seconds.

---

## Day 4 — Team Training

| Task | Owner | DoD | Est. Hours |
|------|-------|-----|------------|
| Deliver Runbook walkthrough to team | AI Champion | Team completes a dry-run of the incident Runbook | 4h |

**Verification:** Runbook dry-run log confirms all steps executed without operator prompts.

---

## Day 5 — Monitoring Deployment

| Task | Owner | DoD | Est. Hours |
|------|-------|-----|------------|
| Deploy `governance_dashboard.py` | On-call | Dashboard renders without errors | 0.5h |
| Deploy `health_dashboard.py` | On-call | Health dashboard shows all services UP | 0.5h |

**Verification:** Both dashboards are reachable and display live data.

---

## Definition of Done (DoD)

All items must pass their DoD criteria before the week is considered complete. Open a follow-up ticket for any item that cannot be verified on the scheduled day.
