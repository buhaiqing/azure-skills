---
name: azure-skill-generator
description: >-
  Use when creating or scaffolding a new Azure cloud resource/service operational
  skill (azure-[service]-ops) in this repository. Generates skill structure from
  Azure official documentation, API/SDK references. Not for executing live Azure
  operations.
license: MIT
compatibility: >-
  Access to Azure official documentation, Azure CLI docs, Azure SDK for Python (3.10+)
  references, azure-skill-generator/references/azure-skill-template.md, and agentskills.io
  frontmatter conventions.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-05-10"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  type: meta-skill
---

# Azure Skill Generator (Meta-Skill)

## What This Skill Does

This **meta-skill** scaffolds new Azure operational skills (`azure-[service]-ops`) for this repository. It does NOT execute live Azure operations—use the generated skills for that.

## When to Use

| Use This Skill | Do NOT Use |
|----------------|------------|
| Creating a new Azure service skill | Executing Azure operations directly |
| Aligning existing skill to template | Billing-only or IAM-only tasks |
| Updating skill after Azure API changes | Non-Azure cloud work |

## Generation Process Overview

```
Input → Analyze Sources → Create Layout → Populate Files → Verify
```

## Environment Setup (.env Support)

This meta-skill uses `.env` for credential management. The setup script automates initialization and config generation.

### One-time Setup

```bash
# Initialize .env from .env.example and generate config
python azure-skill-generator/scripts/setup_env.py
```

This will:
1. Copy `.env.example` → `.env` (if `.env` does not exist)
2. Validate that required Azure credentials are set
3. Generate `azure-skill-generator/config.yaml` with actual values from `.env`
4. Render `assets/example-config.yaml` with `{{env.*}}` placeholders resolved

### Subsequent Updates

```bash
# After editing .env, re-render config files
python azure-skill-generator/scripts/setup_env.py --render

# Check if credentials are valid
python azure-skill-generator/scripts/setup_env.py --check

# Show current environment status
python azure-skill-generator/scripts/setup_env.py --status
```

### How It Works

| Step | Action |
|------|--------|
| `.env.example` → `.env` | Auto-copy on first run; user fills in credentials |
| `.env` → `config.yaml` | Script reads `.env` and generates the generator's own config |
| `{{env.*}}` → actual values | Placeholders in templates are resolved from `.env` at render time |
| Skill runtime | Generated skills use `{{env.*}}` placeholders resolved from shell env or `.env` |

### Required Azure Variables

| Variable | Purpose |
|----------|---------|
| `AZURE_SUBSCRIPTION_ID` | Azure subscription GUID |
| `AZURE_TENANT_ID` | Azure AD tenant GUID |
| `AZURE_CLIENT_ID` | Service Principal application ID |
| `AZURE_CLIENT_SECRET` | Service Principal client secret |

## Quick Start Checklist

### P0 — MUST Complete
- [ ] Product name + primary resource type identified
- [ ] Official Azure docs URL provided
- [ ] Azure CLI support verified (`az [service] --help`)
- [ ] SDK (Azure SDK for Python/JavaScript) module identified
- [ ] Trigger & Scope with SHOULD/SHOULD-NOT defined
- [ ] `{{env.*}}` placeholders (no secret literals)
- [ ] Execution flows: Pre-flight → Execute → Validate → Recover
- [ ] Safety gates for destructive operations
- [ ] Dual-path: Azure CLI (primary) + Azure SDK (fallback)

### P1 — SHOULD Complete
- [ ] Cross-service delegation documented
- [ ] Idempotency behavior documented
- [ ] Response JSON paths verified with real runs
- [ ] Troubleshooting error code table

## Directory Layout

```
azure-[service]-ops/
├── SKILL.md              # What to do (triggers, scope, flows)
├── references/
│   ├── azure-cli-usage.md  # How to: CLI commands, JSON paths
│   ├── azure-sdk-usage.md # How to: SDK methods, examples
│   ├── core-concepts.md  # Service architecture, limits
│   ├── troubleshooting.md # Error codes, diagnostics
│   └── integration.md    # Environment setup (credentials)
│   └── governance-review.md # Pre-merge checklist
└── assets/
    └── example-config.yaml
```

## Key Principles

| Principle | Enforcement |
|-----------|-------------|
| **CLI-first with SDK fallback** | Primary path: Azure CLI; fallback: Azure SDK after 3 CLI failures |
| **OpenAPI accuracy** | All fields traceable to Azure REST API docs |
| **Safety gates** | Human confirmation before destructive operations |
| **Credential isolation** | Only `{{env.*}}` placeholders; never real secrets |

## Azure vs AWS Key Differences

| Aspect | Azure | AWS |
|--------|-------|-----|
| CLI tool | `az` (Azure CLI) | `aws` (AWS CLI) |
| Primary SDK | Azure SDK for Python (`azure-*`) | boto3 |
| Auth method | Service Principal / Azure AD | IAM User / Role |
| Resource ID format | `/subscriptions/.../resourceGroups/.../providers/...` | ARN (`arn:aws:...`) |
| Output format | JSON (default) | JSON (--output json) |
| Region term | "Location" | "Region" |
| Container | "Resource Group" | No direct equivalent |

## Variable Convention (Azure)

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure region (e.g., eastus, westeurope) |
| `{{user.resource_name}}` | User input | Ask once; reuse |
| `{{output.resource_id}}` | Last API response | Parse per Azure REST API docs |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Reference Files (How to Details)

| Reference | Content |
|-----------|---------|
| [azure-skill-template.md](references/azure-skill-template.md) | Full skill template structure |
| [azure-cli-conventions.md](references/azure-cli-conventions.md) | CLI behavioral notes, output handling, retry strategy |
| [azure-sdk-usage.md](references/azure-sdk-usage.md) | Azure SDK patterns, error handling, polling |
| [integration.md](references/integration.md) | Environment setup (Service Principal, credentials) |
| [core-concepts-template.md](references/core-concepts-template.md) | Service architecture template |
| [troubleshooting-template.md](references/troubleshooting-template.md) | Error codes, diagnostics template |
| [governance-review.md](references/governance-review.md) | Pre-merge checklist, adversarial scenarios |

## See Also

- [Azure CLI Documentation](https://docs.microsoft.com/cli/azure/)
- [Azure SDK for Python](https://docs.microsoft.com/python/api/overview/azure/)
- [Azure REST API Reference](https://docs.microsoft.com/rest/api/azure/)
- [Agent Skills OpenSpec](https://agentskills.io/specification)