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
