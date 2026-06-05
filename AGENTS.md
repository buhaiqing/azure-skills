# AGENTS.md

Repo-specific guidance for AI agents working in `azure-skills`. Read this before touching anything.

## What this repo is

A collection of **prompt-only "skills"** for AI agents, not runnable application code. Each top-level `azure-*-ops/` directory is a skill consumed by an Agent runtime (Harness AI, Claude Code, OpenCode, Cursor, etc.) that loads `SKILL.md` and lazy-loads `references/*.md` on demand.

There is no build, no test suite, no CI. The "deliverable" is markdown that an Agent will follow when operating real Azure resources.

`azure-skill-generator/` is a **meta-skill**: it scaffolds new `azure-[service]-ops/` skills. It is the only thing in the repo with executable code (`scripts/setup_env.py`).

## Skill anatomy (must match exactly)

Every `azure-*-ops/` skill follows this layout. Diverging breaks the runtime contract.

```
azure-[service]-ops/
├── SKILL.md                  # ~100-150 lines, What to do (triggers, scope, flows)
├── references/
│   ├── core-concepts.md      # service architecture
│   ├── troubleshooting.md    # error codes, diagnostics
│   └── integration.md        # credentials / env setup
└── assets/
    └── example-config.yaml   # uses {{env.*}} placeholders only
```

`SKILL.md` MUST start with YAML frontmatter (`name`, `description`, `license`, `compatibility`, `metadata.*`). Mirror an existing skill (e.g. `azure-aks-ops/SKILL.md`) — frontmatter shape is part of the agentskills.io spec the runtimes parse.

When generating or modifying a skill, the source of truth for structure, frontmatter, variable conventions, and review gates is `azure-skill-generator/references/` — not your prior knowledge. Use:
- `azure-skill-template.md` for skeleton
- `azure-cli-conventions.md` and `azure-sdk-usage.md` for command/SDK patterns
- `governance-review.md` as the pre-merge checklist (run this mentally before claiming done)

## Hard rules

1. **Never write real credentials anywhere.** All credential references must use `{{env.AZURE_*}}` placeholders. `.env` is gitignored and `azure-skill-generator/config.yaml` is gitignored *because it is generated from .env and contains secrets*.
2. **Dual-path execution**: every operation in a skill must document Azure CLI primary + Azure SDK for Python fallback. CLI failures retry up to 3× before falling back.
3. **Destructive operations** (`delete`, `terminate`, `purge`, scaling down to 0) MUST include an explicit human-confirmation gate in the skill text. Reviewers reject skills missing this.
4. **Azure terminology**: always "Resource Group" (required for nearly every resource) and "Location" (not "region"). Resource IDs use full `/subscriptions/.../providers/...` form.
5. **Variable convention** is enforced: `{{env.*}}` for secrets (never ask user), `{{user.*}}` for inputs (ask once, reuse), `{{output.*}}` for parsed API responses. See `azure-skill-generator/SKILL.md` "Variable Convention".

## Skill update workflow (project directive)

After *any* edit to a `SKILL.md` or its `references/`, run **2 rounds of self-review** against `azure-skill-generator/references/governance-review.md` (Pre-Merge Checklist + Adversarial Scenarios A–I + Azure-specific Governance Rules). Fix every issue surfaced — do not defer. Only stop when round N+1 produces zero new findings or N == 2 with all findings resolved.

Typical issues that surface in self-review:
- Missing safety gate on delete/scale-down
- `{{env.*}}` placeholders replaced with literals by accident
- Cross-service work that should delegate to a sibling skill instead of inlining
- JSON output paths not verified (`--output json` assumed but field names guessed)
- Recovery table missing HALT-vs-retry decision for quota / throttling / 5xx
- **Token Efficiency**: TE-1~TE-7 violations (see [docs/token-efficiency.md](./docs/token-efficiency.md))

**自检流程**：Round 1 基础检查 → Round 2 关键分析。详见 [docs/token-efficiency.md](./docs/token-efficiency.md)。

## Setup script — known footguns

`azure-skill-generator/scripts/setup_env.py` is the only Python in the repo. Important behaviors:

- `setup_env.py` (no args) → copies `.env.example` → `.env` *only if missing*, then validates and renders. Safe to re-run.
- `--render` **overwrites `azure-skill-generator/assets/example-config.yaml` in place**, replacing `{{env.*}}` with resolved values. The original template form is lost after one run. If you need to preserve placeholders (e.g. after rendering), restore them with `git checkout -- azure-skill-generator/assets/example-config.yaml` before committing. Never commit a rendered version.
- `--check` validates env without writing files. Use this when you only want to verify credentials.
- `--status` prints masked credential state.

Run from repo root: `python azure-skill-generator/scripts/setup_env.py [--check|--render|--status]`. Requires Python ≥ 3.10.

## Adding a new skill

1. Gather: official Azure docs URL, primary resource type, `az [service] --help` output, `azure.mgmt.[service]` SDK module name, operation list.
2. Copy the structure of an existing skill that is closest in shape (e.g. `azure-aks-ops` for cluster-style resources, `azure-blobstorage-ops` for data-plane, `azure-loadbalancer-ops` for networking).
3. Replace per `azure-skill-template.md`. Keep SKILL.md ~100–150 lines; push detail into `references/`.
4. Update both `README.md` and `README_cn.md`: the project-structure tree, the "Existing Skills" table, and any comparison tables the new service belongs in. Both READMEs must stay in sync.
5. Run the 2-round self-review described above.

## Existing skills (do not duplicate scope)

Network: `azure-loadbalancer-ops` (L4), `azure-appgateway-ops` (L7+WAF), `azure-frontdoor-ops` (global L7+CDN), `azure-trafficmanager-ops` (DNS).
Compute/Container: `azure-vm-ops`, `azure-aks-ops`.
Storage: `azure-blobstorage-ops`.
Observability: `azure-monitor-ops`.
Meta: `azure-skill-generator`.

If a user request straddles services, the skill should delegate (e.g. `azure-aks-ops` defers ACR to a future `azure-acr-ops`) rather than inline cross-service logic.

## Things to avoid

- Generic "best practice" prose. Every line in a SKILL.md is read by an Agent at runtime — token waste matters.
- Adding lockfiles, requirements.txt, or build configs. There is no Python package here; `setup_env.py` uses only stdlib.
- Speculative `az` flags or SDK fields. If unverified against current Azure docs, omit.
- Committing `.env`, `azure-skill-generator/config.yaml`, or any `.DS_Store` (already gitignored; do not force-add).
- Editing only `README.md` without `README_cn.md` (or vice versa). They are kept in lockstep.

---

## Generator-Critic-Loop (GCL) — Adversarial Quality Gate

> Inspired by GAN's Generator/Discriminator idea, but deliberately **not** a real GAN.
> Naming: **GCL (Generator-Critic-Loop)** to avoid misleading reviewers and LLM trainees.
> Adapted from `qcloud-skills/AGENTS.md` GCL spec for the Azure (`az` / `azure.mgmt.*`) execution path.

### 1. Purpose

Apply an adversarial **Generator ↔ Critic** loop with a quantitative rubric to every skill execution.
Most valuable in **high-side-effect cloud operations** (delete, stop, restore, RBAC, KMS, DDL) where a single
mistake is unrecoverable.

| GAN (real) | GCL (this spec) |
|---|---|
| Discriminator learns sample distribution | Critic scores an **explicit rubric** |
| No termination condition | Must terminate: **PASS / MAX_ITER / SAFETY_FAIL** |
| G and D train in parallel | G and C run **sequentially** |
| Goal: "fool the D" | Goal: "pass the rubric threshold" |

### 2. Roles

| Role | Job | Input | Output | Forbidden |
|---|---|---|---|---|
| **Generator (G)** | Execute the cloud operation | user request + previous Critic feedback | result + execution trace | modifying the rubric; self-scoring |
| **Critic (C)** | Independently audit G's output | G's result + trace + rubric | scores + suggestions | calling `az` / SDK / mutating anything |
| **Orchestrator (O)** | Loop control, termination, final return | context + C scores + budget | continue / final result | executing or scoring on its own |

**Hard constraint:** G and C MUST live in **isolated prompt contexts** (preferably isolated sessions
or sub-agents). A shared context is a "pseudo-GCL" and is explicitly banned — see §9.

### 3. Rubric (mandatory per skill)

Each `SKILL.md` MUST declare its skill-specific rubric. Minimum 5 dimensions:

| Dimension | Meaning | Scale | Default threshold |
|---|---|---|---|
| **Correctness** | Resource id / state / config actually matches the request | 0 / 0.5 / 1 | ≥ 0.5 (1.0 required for `delete` / `stop` / RBAC / KMS / DDL) |
| **Safety** | Destructive op (`delete` / `stop` / `deallocate` / RBAC / KMS / DDL) was confirmed or guarded | 0 / 1 | = 1 |
| **Idempotency** | Retrying the same call will not cause duplicate side-effects | 0 / 0.5 / 1 | ≥ 0.5 |
| **Traceability** | Output is auditable: command, params, raw response, errors all captured | 0 / 0.5 / 1 | ≥ 0.5 |
| **Spec Compliance** | Conforms to the skill's `core-concepts.md` / `azure-cli-conventions.md` constraints | 0 / 0.5 / 1 | ≥ 0.5 |

**Safety = 0 → ABORT immediately, regardless of total score.**

### 4. Loop Flow

```
User Request
     │
     ▼
[0] Pre-flight (Orchestrator)
    - resolve env.* and user.* variables
    - pick skill, load its rubric
     │
     ▼
[1] Generate (G) ───────────────────────┐
    - run az / azure.mgmt.* SDK          │
    - capture trace                     │
     │                                  │
     ▼                                  │
[2] Critique (C)                       │
    - isolated prompt context           │
    - score every rubric dimension      │
    - emit actionable suggestions       │
     │                                  │
     ▼                                  │
[3] Decide (Orchestrator)              │
    - Safety=0  → ABORT (no partial)   │
    - all pass  → RETURN                │
    - else & iter<max → inject         │
       suggestions into G               │
    - else → RETURN best + unresolved   │
       rubric items                     │
     └──────────────────────────────────┘
```

### 5. Termination (first match wins)

| Condition | Behavior |
|---|---|
| **PASS** | Every rubric dimension meets its threshold → return G's result |
| **MAX_ITER** | Reached `max_iterations` (default 3) → return **best-so-far** + unresolved rubric items |
| **SAFETY_FAIL** | Safety = 0 → **ABORT**; never return partial or "best-effort" output |

`max_iterations` defaults per skill class — see §8.

### 6. Trace & Audit (mandatory)

Every GCL run MUST persist a JSON trace:

```json
{
  "skill": "azure-vm-ops",
  "request": "<sanitized user request>",
  "rubric_version": "v1",
  "iterations": [
    {
      "iter": 1,
      "generator": { "command": "az vm delete ...", "args": {...}, "exit_code": 0, "result_excerpt": "..." },
      "critic": {
        "scores": {
          "correctness": 1, "safety": 1, "idempotency": 0.5,
          "traceability": 1, "spec_compliance": 1
        },
        "suggestions": ["..."],
        "blocking": false
      },
      "decision": "RETRY"
    }
  ],
  "final": { "status": "PASS", "iter": 2, "output": "..." }
}
```

Path: `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json`.

### 7. Prompt Templates (mandatory per skill)

Each skill's `references/prompt-templates.md` MUST contain:

1. **Generator Prompt Template** — placeholders: `{{user.request}}`, `{{output.critic_feedback}}`, `{{output.rubric}}`
2. **Critic Prompt Template** — placeholders: `{{output.generator_output}}`, `{{output.trace}}`, `{{output.rubric}}`

> **Placeholder syntax** MUST follow the repository-wide convention (see **Hard rules → Variable convention**):
> `{{env.*}}` / `{{user.*}}` / `{{output.*}}`. Bare `{...}` placeholders are NOT allowed in skill prompt templates.

**Critic prompt must hide the raw user request** to prevent "answer-aligned" rubber-stamping.
Recommended skeleton:

```text
You are an independent cloud-operation auditor.
You will see one execution result and its trace. Score it STRICTLY against the rubric below.
Do NOT consider the original user request — judge only what was actually done.

rubric: {{output.rubric}}
generator_output: {{output.generator_output}}
trace: {{output.trace}}

Return strict JSON:
{
  "scores": { "correctness": 0|0.5|1, "safety": 0|0.5|1, "idempotency": 0|0.5|1,
              "traceability": 0|0.5|1, "spec_compliance": 0|0.5|1 },
  "suggestions": ["≤ 3 concrete, executable improvements"],
  "blocking": true|false
}
```

### 8. Per-Skill Defaults (Azure)

Destructive workload → **required**, max_iter=2. Read-only / advisory → **optional**, max_iter=5. Meta → **optional**, max_iter=3.

| Skill | GCL | Default max_iter | Notes |
|---|---|---|---|
| `azure-vm-ops` | **required** | 2 | `az vm delete` / `az vm deallocate` / `az vm stop` are destructive |
| `azure-aks-ops` | **required** | 2 | `az aks delete` / `az aks stop` destroy the cluster |
| `azure-blobstorage-ops` | **required** | 2 | `az storage container delete` / `az storage account delete` is irreversible |
| `azure-appgateway-ops` | **required** | 2 | `az network application-gateway delete` cuts traffic |
| `azure-loadbalancer-ops` | **required** | 2 | `az network lb delete` cuts traffic |
| `azure-frontdoor-ops` | **required** | 2 | `az afd profile delete` / `az afd endpoint purge` |
| `azure-trafficmanager-ops` | **required** | 2 | `az network traffic-manager profile delete` disrupts DNS routing |
| `azure-monitor-ops` | recommended | 3 | `az monitor alert-rule delete` / `az monitor action-group delete` |
| `azure-skill-generator` | optional | 3 | meta; must enforce 2-round self-review |

Each skill may override `max_iter` in its own `SKILL.md` (under `## Quality Gate`).

### 9. Anti-Patterns (banned)

- ❌ Shared context G+C | Subjective scoring | Unbounded loop
- ❌ Critic sees user request | Silently downgrade on Safety fail
- ❌ Trace not persisted | Critic mutates resources | Skip self-review
- ❌ Print real credentials in trace → mask `***` always

### 10. Rollout Roadmap

Phase 1: pilot on `azure-vm-ops` | Phase 2: reusable Orchestrator | Phase 3-4: Azure Monitor integration

### 11. Relationship to existing 2-round self-review

GCL is the **runtime** counterpart to the **build-time** "Skill update workflow" above.
They do not overlap:

| Stage | Owner | Purpose |
|---|---|---|
| **Skill update (build time)** | skill author | Diff skill against template; governance-review.md checklist; Scenarios A–I; Azure-specific Rules |
| **Skill execution (runtime)** | Generator + Critic | Score a single execution against the skill's rubric; gate side-effects |

Both gates must pass — a clean self-review does not exempt runtime scoring, and a perfect rubric
does not exempt a sloppy skill update.

### 12. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial GCL specification added to `AGENTS.md` |
| 1.1.0 | 2026-06-05 | Added TE/GCL/LI rules; moved detail to [docs/](./docs/) |

### 13. See also

- Each skill's `references/rubric.md` / `references/prompt-templates.md` — rubric + G/C/O prompts
- [docs/token-efficiency.md](./docs/token-efficiency.md) — TE-1~TE-7 规则 + 内容去重
- [docs/link-integrity.md](./docs/link-integrity.md) — LI-1~LI-4 链接检测
- `azure-skill-generator/references/governance-review.md` — build-time governance review