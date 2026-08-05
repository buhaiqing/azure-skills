# Azure ACR and Key Vault Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add complete `azure-acr-ops` and `azure-keyvault-ops` skills with slim `SKILL.md` entrypoints, detailed references, AIOps/RCA content, GCL artifacts, and README updates.

**Architecture:** Follow the repository skill contract: each skill has a concise `SKILL.md` (~100-150 lines) for triggers, scope, flow, safety gates, and reference links. Detailed Azure CLI, SDK, troubleshooting, AIOps/RCA, rubric, and prompt templates live in `references/`; placeholder-only examples live in `assets/`.

**Tech Stack:** Markdown skill files, YAML examples, Azure CLI, Azure SDK for Python references, repository governance checklist.

---

### Task 1: Inspect Existing Patterns

**Files:**
- Read: `azure-redis-ops/SKILL.md`
- Read: `azure-postgres-ops/SKILL.md`
- Read: `azure-skill-generator/references/governance-review.md`
- Read: `README.md`
- Read: `README_cn.md`

- [x] **Step 1: Read representative files**

Use `Read` on the listed files and note frontmatter shape, slim entrypoint pattern, AIOps/RCA file split, safety gates, GCL references, and README wording conventions.

- [x] **Step 2: Confirm no duplicate directories**

Run: `test ! -e azure-acr-ops && test ! -e azure-keyvault-ops`
Expected: exit 0 before creating new directories.

### Task 2: Create ACR Skill Files

**Files:**
- Create: `azure-acr-ops/SKILL.md`
- Create: `azure-acr-ops/references/core-concepts.md`
- Create: `azure-acr-ops/references/troubleshooting.md`
- Create: `azure-acr-ops/references/integration.md`
- Create: `azure-acr-ops/references/aiops.md`
- Create: `azure-acr-ops/references/rubric.md`
- Create: `azure-acr-ops/references/prompt-templates.md`
- Create: `azure-acr-ops/assets/example-config.yaml`

- [x] **Step 1: Create directories**

Run: `mkdir -p azure-acr-ops/references azure-acr-ops/assets`
Expected: directories exist.

- [x] **Step 2: Write slim `SKILL.md`**

Include YAML frontmatter, trigger/scope, variable convention, JSON paths, execution flow, operation map, safety gates, AIOps/RCA loading guidance, recovery matrix, quality gate, and reference links. Keep detailed commands and RCA rules out of `SKILL.md`.

- [x] **Step 3: Write focused references**

Write the six reference files. Cover registry/repository/tag/manifest operations, AKS image pull RCA, identity/RBAC, firewall/private endpoint/DNS, retention/purge, AIOps correlation, rubric, and GCL prompts.

- [x] **Step 4: Write example config**

Use only `{{env.*}}` and `{{user.*}}` placeholders. Include registry, repository, AKS integration, network, AIOps, and safety sections.

### Task 3: Create Key Vault Skill Files

**Files:**
- Create: `azure-keyvault-ops/SKILL.md`
- Create: `azure-keyvault-ops/references/core-concepts.md`
- Create: `azure-keyvault-ops/references/troubleshooting.md`
- Create: `azure-keyvault-ops/references/integration.md`
- Create: `azure-keyvault-ops/references/aiops.md`
- Create: `azure-keyvault-ops/references/rubric.md`
- Create: `azure-keyvault-ops/references/prompt-templates.md`
- Create: `azure-keyvault-ops/assets/example-config.yaml`

- [x] **Step 1: Create directories**

Run: `mkdir -p azure-keyvault-ops/references azure-keyvault-ops/assets`
Expected: directories exist.

- [x] **Step 2: Write slim `SKILL.md`**

Include YAML frontmatter, trigger/scope, variable convention, JSON paths, execution flow, operation map, safety gates, AIOps/RCA loading guidance, recovery matrix, quality gate, and reference links. Keep detailed commands and RCA rules out of `SKILL.md`.

- [x] **Step 3: Write focused references**

Write the six reference files. Cover vault/secret/key/certificate operations, RBAC vs access policy, managed identity 403 RCA, firewall/private endpoint/DNS, soft-delete/purge protection, certificate expiry, AIOps correlation, rubric, and GCL prompts.

- [x] **Step 4: Write example config**

Use only `{{env.*}}` and `{{user.*}}` placeholders. Include vault, object, identity, network, AIOps, and safety sections. Do not include secret values.

### Task 4: Update README Files

**Files:**
- Modify: `README.md`
- Modify: `README_cn.md`

- [x] **Step 1: Add directories to project tree**

Add `azure-acr-ops` and `azure-keyvault-ops` entries with concise reference descriptions.

- [x] **Step 2: Add rows to Existing Skills**

Add both skills with status complete in English and Chinese tables.

- [x] **Step 3: Keep language versions synchronized**

Ensure both READMEs mention AIOps/RCA coverage consistently.

### Task 5: Governance Self-Review Round 1

**Files:**
- Review all new `SKILL.md` and `references/*.md`

- [x] **Step 1: Apply pre-merge checklist**

Check triggers, `SKILL.md` size, credentials, destructive gates, dual path, JSON paths, recovery, polling, Resource Group, Location, RBAC, and slim-entrypoint compliance.

- [x] **Step 2: Fix concrete issues immediately**

Edit files until all Round 1 checklist findings are resolved.

### Task 6: Governance Self-Review Round 2

**Files:**
- Review all new and modified files

- [x] **Step 1: Apply adversarial scenarios and token-efficiency checks**

Check safety refusals, credential handling, retry limits, API fidelity, cross-service delegation, no generic token-waste sections, and no bloated `SKILL.md` content.

- [x] **Step 2: Fix concrete issues immediately**

Edit files until Round 2 has no unresolved findings.

### Task 7: Final Verification

**Files:**
- Check: all created/modified files

- [x] **Step 1: Verify required files exist**

Run: `for d in azure-acr-ops azure-keyvault-ops; do test -f "$d/SKILL.md" && test -f "$d/references/core-concepts.md" && test -f "$d/references/troubleshooting.md" && test -f "$d/references/integration.md" && test -f "$d/references/aiops.md" && test -f "$d/references/rubric.md" && test -f "$d/references/prompt-templates.md" && test -f "$d/assets/example-config.yaml"; done`
Expected: exit 0.

- [x] **Step 2: Verify slim `SKILL.md` size**

Run: `wc -l azure-acr-ops/SKILL.md azure-keyvault-ops/SKILL.md`
Expected: each file near 100-150 lines; if above 160, move detail into references.

- [x] **Step 3: Verify no obvious secret literals**

Run targeted searches for `TODO`, `TBD`, `AccountKey=`, `password:`, `client_secret:`, `secret_value`, and token-like literals in new files. Expected: only placeholders or explanatory text, no real secrets.

- [x] **Step 4: Review git diff**

Run: `git diff --stat && git diff -- README.md README_cn.md`
Expected: new skill directories, README updates, and this plan file only.
