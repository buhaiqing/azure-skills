# User Guide — azure-skills

Single path from first skill load to Microsoft Level 400 Capable (repo) operations.

## 1. Setup

```bash
python azure-skill-generator/scripts/setup_env.py --check
# Credentials live in .env as {{env.AZURE_*}} — never paste into chat
```

## 2. Load a skill

Point your Agent runtime at `azure-<service>-ops/SKILL.md` (runtime-agnostic).
Follow triggers / SHOULD-NOT / Quality Gate in that file.

## 3. Quality gate (GCL)

```bash
python3 scripts/gcl_runner.py --skill azure-vm-ops --critic rule
# Optional semantic critic: --critic llm  (CRITIC_PROVIDER + API key)
```

## 4. L4 auto-feedback loop

```bash
python3 scripts/auto_feedback_loop.py \
  --skill azure-vm-ops \
  --operation vm_create \
  --command "az vm create --name ..." \
  --desired-state '{"powerState":"VM running"}'
```

Risk tiers (`scripts/risk_tiers.json`) auto-block R2 destructive ops into human escalation.

## 5. Cross-skill diagnose

```bash
python3 scripts/orchestrator.py --diagnose "<symptom>"
```

## 6. Health, canary, value

```bash
python3 scripts/run_all_scenarios.py              # mock suite
python3 scripts/live_canary.py --dry-run          # config contract
python3 scripts/live_canary.py --env=live         # needs AZURE_RESOURCE_GROUP
python3 scripts/metrics_collector.py
python3 scripts/health_dashboard.py --azure-monitor
python3 scripts/eval_weekly.py
python3 scripts/value_report.py
```

## 7. Proactive watch

```bash
python3 scripts/watch_and_heal.py --alerts-file scripts/sample_alerts.json
```

## 8. Adoption

- [adoption-tiers](./adoption-tiers.md) — sandbox → enterprise
- [governance-federation](./governance-federation.md) — R0/R1/R2 approvals
- [human-agent-ops-playbook](./human-agent-ops-playbook.md) — E2E ops flow

## Wording discipline

| Phrase | Meaning |
|--------|---------|
| **Gartner L4 Certified** | Mock-backed observe→diff→heal→escalate (2026-07-27) |
| **Microsoft Level 400 Capable (repo)** | DoD in `docs/superpowers/plans/ms-l400-roadmap.md` |

Do not use these interchangeably.
