# Adoption Tiers — sandbox → team → enterprise

MS Level 400 Organization enablement starter kit for azure-skills adopters.

## Tiers

| Tier | Subscription posture | Allowed tiers | Critic | Monitor ingest |
|------|----------------------|---------------|--------|----------------|
| **Sandbox** | Disposable RG; no prod data | R0–R1; R2 only on disposable names | rule | Optional |
| **Team** | Shared non-prod | R0–R1; R2 with dual confirm | rule or LLM | Weekly dashboard |
| **Enterprise** | Prod + change window | R0 free; R1 change ticket; R2 CAB | LLM + rule fallback | Continuous + alerts → `watch_and_heal` |

## CoE / Champion checklist (minimal)

- [ ] Name an executive sponsor and platform owner
- [ ] Publish this repo + `manual/user-guide.md` in internal docs
- [ ] Enforce CI (`Skill ALM` workflow) on forks/mirrors
- [ ] Map Pager/Teams webhook to `audit-results/watch-and-heal-last.json`
- [ ] Monthly `value_report.py` review in AI Council
- [ ] Quarterly RAI spot-check (governance-review RAI section)

## Champion responsibilities

1. Keep `risk_tiers.json` overrides aligned with org policy
2. Train on-call to escalate via Trace ID (never re-run blind)
3. Block promotion sandbox → enterprise until live canary passes for core skills

See [coe-starter-kit](./coe-starter-kit/README.md) for the complete first-week action kit.

## Related

- [governance-federation](./governance-federation.md)
- [ms-agentic-maturity-baseline](../docs/superpowers/reports/ms-agentic-maturity-baseline.md)
