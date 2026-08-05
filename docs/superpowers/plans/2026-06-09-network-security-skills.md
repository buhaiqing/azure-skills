# Azure Network Security Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `azure-nsg-ops` and `azure-privateendpoint-ops` as complete prompt-only Azure operation skills.

**Architecture:** Each skill follows the repository runtime contract: slim `SKILL.md`, detailed `references/`, and placeholder-only `assets/example-config.yaml`. README files are updated in lockstep, including existing README_cn drift.

**Tech Stack:** Markdown skill files, YAML example config, Azure CLI primary path, Azure SDK for Python `azure.mgmt.network` fallback path.

---

### Task 1: Create `azure-nsg-ops`

**Files:**
- Create: `azure-nsg-ops/SKILL.md`
- Create: `azure-nsg-ops/references/core-concepts.md`
- Create: `azure-nsg-ops/references/troubleshooting.md`
- Create: `azure-nsg-ops/references/integration.md`
- Create: `azure-nsg-ops/references/rubric.md`
- Create: `azure-nsg-ops/references/prompt-templates.md`
- Create: `azure-nsg-ops/assets/example-config.yaml`

- [x] Write slim `SKILL.md` with frontmatter, trigger/scope, variable convention, CLI primary + SDK fallback flow, destructive confirmation gates, GCL quality gate, and references.
- [x] Write reference docs covering NSG concepts, troubleshooting, integration, rubric, and prompt templates.
- [x] Write placeholder-only example config.

### Task 2: Create `azure-privateendpoint-ops`

**Files:**
- Create: `azure-privateendpoint-ops/SKILL.md`
- Create: `azure-privateendpoint-ops/references/core-concepts.md`
- Create: `azure-privateendpoint-ops/references/troubleshooting.md`
- Create: `azure-privateendpoint-ops/references/integration.md`
- Create: `azure-privateendpoint-ops/references/rubric.md`
- Create: `azure-privateendpoint-ops/references/prompt-templates.md`
- Create: `azure-privateendpoint-ops/assets/example-config.yaml`

- [x] Write slim `SKILL.md` with frontmatter, trigger/scope, variable convention, CLI primary + SDK fallback flow, destructive confirmation gates, GCL quality gate, and references.
- [x] Write reference docs covering Private Endpoint concepts, troubleshooting, integration, rubric, and prompt templates.
- [x] Write placeholder-only example config.

### Task 3: Update README files

**Files:**
- Modify: `README.md`
- Modify: `README_cn.md`

- [x] Add both new skills to the project tree.
- [x] Add both new skills to Existing Skills tables.
- [x] Add NSG and Private Endpoint to networking comparison tables.
- [x] Bring README_cn into lockstep with README by adding missing AKS, Blob Storage, VM, Storage Services, and Container Services entries.

### Task 4: Governance self-review and code review

**Files:**
- Review against: `azure-skill-generator/references/governance-review.md`

- [x] Run Round 1 self-review: triggers, structure, credentials, destructive gates, dual path, placeholders, terminology, token efficiency, link integrity.
- [x] Fix all Round 1 findings.
- [x] Run Round 2 self-review: adversarial scenarios and Azure-specific governance rules.
- [x] Fix all Round 2 findings.
- [x] Request code review with `requesting-code-review` and fix all findings.

### Task 5: Verify, commit, and push

**Files:**
- All modified files

- [x] Run verification commands for file presence, placeholder safety, broken links, and git diff review.
- [x] Commit changes with a focused message.
- [x] Push the commit to the current branch after final confirmation.
