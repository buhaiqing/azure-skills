# Azure Redis and PostgreSQL Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add complete `azure-redis-ops` and `azure-postgres-ops` skills with AIOps/RCA troubleshooting content and repository documentation updates.

**Architecture:** Follow the existing prompt-only skill layout: one concise `SKILL.md` per service, detailed service knowledge in focused `references/*.md`, and placeholder-only `assets/example-config.yaml`. Each skill has dual Azure CLI + Python SDK paths, human gates for destructive/disruptive operations, and GCL runtime artifacts (`rubric.md`, `prompt-templates.md`).

**Tech Stack:** Markdown skill files, YAML examples, Azure CLI, Azure SDK for Python references, repository governance checklist.

---

### Task 1: Inspect Existing Patterns

**Files:**
- Read: `azure-vm-ops/SKILL.md`
- Read: `azure-blobstorage-ops/references/troubleshooting.md`
- Read: `azure-skill-generator/references/azure-skill-template.md`
- Read: `azure-skill-generator/references/governance-review.md`

- [ ] **Step 1: Read representative files**

Use `Read` on the listed files and note frontmatter, operation sections, safety gates, GCL references, and README wording conventions.

- [ ] **Step 2: Confirm no duplicate directories**

Run: `test ! -e azure-redis-ops && test ! -e azure-postgres-ops`
Expected: exit 0 before creating new directories.

### Task 2: Create Redis Skill Files

**Files:**
- Create: `azure-redis-ops/SKILL.md`
- Create: `azure-redis-ops/references/core-concepts.md`
- Create: `azure-redis-ops/references/troubleshooting.md`
- Create: `azure-redis-ops/references/integration.md`
- Create: `azure-redis-ops/references/aiops.md`
- Create: `azure-redis-ops/references/rubric.md`
- Create: `azure-redis-ops/references/prompt-templates.md`
- Create: `azure-redis-ops/assets/example-config.yaml`

- [ ] **Step 1: Create directories**

Run: `mkdir -p azure-redis-ops/references azure-redis-ops/assets`
Expected: directories exist.

- [ ] **Step 2: Write `SKILL.md`**

Include YAML frontmatter, trigger/scope, variables, JSON paths, operation flow, Redis operations, AIOps/RCA loading guidance, safety gates, recovery matrix, quality gate, and references.

- [ ] **Step 3: Write focused references**

Write the six reference files. Keep `SKILL.md` concise; put detailed metric/root-cause rules in `troubleshooting.md` and `aiops.md`.

- [ ] **Step 4: Write example config**

Use only `{{env.*}}` and `{{user.*}}` placeholders. Do not include real credentials.

### Task 3: Create PostgreSQL Skill Files

**Files:**
- Create: `azure-postgres-ops/SKILL.md`
- Create: `azure-postgres-ops/references/core-concepts.md`
- Create: `azure-postgres-ops/references/troubleshooting.md`
- Create: `azure-postgres-ops/references/integration.md`
- Create: `azure-postgres-ops/references/aiops.md`
- Create: `azure-postgres-ops/references/rubric.md`
- Create: `azure-postgres-ops/references/prompt-templates.md`
- Create: `azure-postgres-ops/assets/example-config.yaml`

- [ ] **Step 1: Create directories**

Run: `mkdir -p azure-postgres-ops/references azure-postgres-ops/assets`
Expected: directories exist.

- [ ] **Step 2: Write `SKILL.md`**

Cover PostgreSQL Flexible Server operations, networking/firewall, backup/restore, start/stop/restart, metrics/logs, AIOps/RCA, safety gates, recovery, and quality gate.

- [ ] **Step 3: Write focused references**

Include core concepts, integration/RBAC/SDK, scenario-rich troubleshooting, AIOps correlation rules, rubric, and GCL prompt templates.

- [ ] **Step 4: Write example config**

Use placeholder-only config for server, database, networking, monitoring, and analysis windows.

### Task 4: Update README Files

**Files:**
- Modify: `README.md`
- Modify: `README_cn.md`

- [ ] **Step 1: Add directories to project tree**

Add Redis and PostgreSQL sections after storage/observability or near data services.

- [ ] **Step 2: Add rows to Existing Skills**

Add `azure-redis-ops` and `azure-postgres-ops` with status complete in both languages.

- [ ] **Step 3: Keep language versions synchronized**

Ensure both READMEs mention AIOps/RCA coverage consistently.

### Task 5: Governance Self-Review Round 1

**Files:**
- Review all new `SKILL.md` and `references/*.md`

- [ ] **Step 1: Apply pre-merge checklist**

Check triggers, credentials, destructive gates, dual path, JSON paths, recovery, polling, Resource Group, Location, and RBAC.

- [ ] **Step 2: Fix concrete issues immediately**

Edit files until all Round 1 checklist findings are resolved.

### Task 6: Governance Self-Review Round 2

**Files:**
- Review all new and modified files

- [ ] **Step 1: Apply adversarial scenarios and token-efficiency checks**

Check safety refusals, credential handling, retry limits, API fidelity, cross-service delegation, and no generic token-waste sections.

- [ ] **Step 2: Fix concrete issues immediately**

Edit files until Round 2 has no unresolved findings.

### Task 7: Final Verification

**Files:**
- Check: all created/modified files

- [ ] **Step 1: Verify required files exist**

Run: `for d in azure-redis-ops azure-postgres-ops; do test -f "$d/SKILL.md" && test -f "$d/references/core-concepts.md" && test -f "$d/references/troubleshooting.md" && test -f "$d/references/integration.md" && test -f "$d/references/aiops.md" && test -f "$d/references/rubric.md" && test -f "$d/references/prompt-templates.md" && test -f "$d/assets/example-config.yaml"; done`
Expected: exit 0.

- [ ] **Step 2: Verify no obvious secret literals**

Run targeted searches for `client_secret`, `password:`, and `AccountKey=` in new files. Expected: only placeholders or explanatory text, no real values.

- [ ] **Step 3: Review git diff**

Run: `git diff --stat && git diff -- README.md README_cn.md`
Expected: new skills and README updates only, plus this plan file.
