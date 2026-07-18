# Plan: P1 Azure Skills Development (Batch 1)

Status: DRAFT — pending approval
Scope: Implement the 6 P1 skills from `README.md` → Planned Skills (Roadmap).
Source of truth for structure/frontmatter/variable conventions: `azure-skill-generator/references/`.

## Goal

Bring the repo from 19 shipped skills to 25 by adding the highest-value, highest-frequency
Azure services that are currently un-encapsulated: compute (Functions, ACI), data
(SQL DB, Cosmos DB), and messaging (Service Bus, Event Hubs).

## Batch order (priority + dependency)

| # | Skill | Service | Class | Why this order |
|---|-------|---------|-------|----------------|
| 1 | `azure-function-ops` | Azure Functions | Compute (serverless) | Largest compute gap; no dependency on others |
| 2 | `azure-sqldb-ops` | Azure SQL Database | Data (relational) | Paired thinking with existing `azure-postgres-ops` |
| 3 | `azure-cosmos-ops` | Azure Cosmos DB | Data (NoSQL) | AIOps/RCA value high; independent |
| 4 | `azure-aci-ops` | Azure Container Instances | Compute (serverless containers) | Complements `azure-aks-ops`/`azure-acr-ops`; delegate, don't inline |
| 5 | `azure-servicebus-ops` | Azure Service Bus | Messaging | Independent; dead-letter/quota RCA |
| 6 | `azure-eventhub-ops` | Azure Event Hubs | Messaging (streaming) | Independent; partition/throughput RCA |

No hard dependency between skills — order is by impact. Each skill is independently
shippable; do not block one on another.

## Per-skill workflow (mandatory, from AGENTS.md)

For EACH skill, in order:

1. **Scaffold** with `azure-skill-generator` (mirror closest existing skill shape):
   - Compute-shaped → mirror `azure-vm-ops` / `azure-aks-ops`
   - Data-shaped → mirror `azure-postgres-ops`
   - Messaging-shaped → mirror `azure-redis-ops`
2. **Author** `SKILL.md` (~100–150 lines) + `references/{core-concepts,troubleshooting,integration}.md`
   + `assets/example-config.yaml` ({{env.*}} only).
3. **Dual-path**: every operation documents Azure CLI primary + Azure SDK for Python fallback
   (CLI retry ≤3× before fallback).
4. **Safety gate**: any `delete`/`purge`/`scale-to-0` MUST carry an explicit human-confirmation gate.
5. **GCL**: optional for these (non-destructive by default), enable if a skill adds a destructive op.
6. **2-round self-review** against `azure-skill-generator/references/governance-review.md`
   (Pre-Merge Checklist + Scenarios A–I). Fix every finding; stop when round N+1 = 0 new.
7. **Critical-reflection review** (new AGENTS.md rule): critique → fix all → re-review → repeat
   until a round is clean.
8. **Update READMEs**: add the new skill to both `README.md` and `README_cn.md`
   (Existing Skills table + any relevant comparison table). Keep in lockstep.
9. **Commit + push** each skill as its own commit (per GCL: one CR = one commit).

## Acceptance / Definition of Done

A skill is DONE only when ALL hold:
- [ ] `SKILL.md` matches `azure-skill-template.md` frontmatter + ~100–150 lines
- [ ] All `references/` present and linked (not inlined in SKILL.md)
- [ ] No literal credentials; only `{{env.AZURE_*}}` placeholders
- [ ] Destructive ops have human-confirmation gate
- [ ] JSON field names verified against `az <svc> --help` (not guessed)
- [ ] 2-round self-review clean + critical-reflection round clean
- [ ] Both READMEs updated and in sync
- [ ] Committed & pushed, working tree clean

## Out of scope (this batch)

P2 (Queue/File Storage, Backup, Site Recovery, DNS) and P3 (Logic Apps, Event Grid,
APIM, Synapse, IoT Hub) — deferred to later batches.

## Risks / notes

- Do NOT inline cross-service logic (e.g. ACI should delegate ACR pushes to `azure-acr-ops`,
  not re-document it).
- Specifying `az` flags/SDK fields only when verified against current Azure docs; omit if unverified.
- Keep token efficiency (TE-1~TE-7): no best-practice prose bloat in SKILL.md.
