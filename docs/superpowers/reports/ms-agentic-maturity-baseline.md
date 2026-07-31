# Microsoft Agentic AI Maturity Baseline — azure-skills

> Date: 2026-08-01
> Scope: Repository-deliverable capabilities only (not customer CoE org design)
> Framework: [Microsoft Agentic AI Adoption Maturity Model](https://learn.microsoft.com/en-us/agents/adoption-maturity-model/)

## Boundary

This baseline scores what **azure-skills** can prove as a platform asset.
It does **not** claim an adopting enterprise has Organization & Culture = 400 —
that requires customer CoE, sponsors, and change management.

| Claim language | Meaning |
|----------------|---------|
| Gartner L4 Certified | Observe → Diff → Heal → Escalate with mock evidence ([l4-certification](./l4-certification-2026-07-27.md)) |
| Microsoft Level 400 Capable (repo) | DoD in [ms-l400-roadmap](../plans/ms-l400-roadmap.md) met |

## Gartner L4 ↔ Microsoft Level mapping

| Capability | Gartner L4 | MS Level 300 | MS Level 400 | MS Level 500 |
|------------|------------|--------------|--------------|--------------|
| Observe/Diff/Heal loop | Required | Defined ops | Proactive + monitored | Predictive / continuous |
| Human confirmation on destructive | Required | Documented | Risk-tiered federation | Always-on controls |
| Cross-system orchestration | Optional+ | Single-agent standards | Cross-system / multi-skill | Advanced multi-agent |
| Telemetry & evaluation | Trace files | ALM + basic telemetry | Centralized + automated eval | Self-improving |
| Business value KPIs | Tech metrics | Primary metrics defined | Measurable optimization loops | Continuous optimization |
| Production evidence | Mock OK for cert | Defined | Live / enterprise-grade | Continuous |

## Pillar scores (repo-controllable)

| Pillar | Level | Evidence | Scale-breaker to 400 |
|--------|-------|----------|----------------------|
| Technology and data | 300 | 31 skills, GCL, auto_feedback_loop, orchestrator, memory, health_dashboard | Live canary, Azure Monitor ingest, Skill ALM CI |
| AI governance and security | 300 | Safety gates, Safety=0 abort, traces, escalate | Risk tiers, watch→heal, RAI in governance-review |
| Business strategy | 250 | CostObserver, L4 tech metrics | value_report, human-agent playbook |
| AI strategy and experience | 250 | Skill taxonomy, dual-path CLI/SDK | Explicit MS↔Gartner roadmap + maturity self-assess |
| Organization and culture | 200 | manual/, README | Adoption tiers + CoE starter kit |

**Ceiling rule**: weakest pillar caps claimed maturity. Pre-plan ceiling ≈ **Defined (300)** on Technology/Governance; Culture/Strategy trail.

## Three scale-breakers (priority)

1. **Production evidence** — mock-only certification ≠ MS Technology 400
2. **Proactive governance telemetry** — Monitor → remediate path + risk tiers
3. **Value KPIs** — business-reportable outcomes beyond heal rate

## Post-plan target

After Waves 0–4 DoD: claim **Microsoft Level 400 Capable (repository capability)** with explicit Culture caveat.

**Readiness:** [ms-l400-readiness-2026-08-01.md](./ms-l400-readiness-2026-08-01.md) — PASS (repo).
