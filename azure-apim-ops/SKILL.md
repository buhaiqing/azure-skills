---
name: azure-apim-ops
description: >-
  Use when operating Azure API Management resources via Azure CLI or Azure SDK;
  user mentions "API Management", "APIM", "apim", API gateway, API products,
  API subscriptions, or APIM policies.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-07-12"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure API Management Operations Skill

## Overview

Azure API Management (APIM) is a managed **API gateway** that publishes, secures, transforms, monitors, and monetizes HTTP APIs. APIM organizes entities into **Service → APIs → Products → Subscriptions**, and applies **Policies** (XML) to control traffic. Slim runbook (~150 lines): triggers, scope, flow, safety gates live here; detailed commands and SDK snippets live in `references/`.

## Trigger & Scope

### SHOULD Use When
- User mentions "API Management", "APIM", "apim"
- Task involves CRUD on APIM Service, API, Product, Subscription, or Policy
- Keywords: api management, apim, api gateway, product, subscription, policy, developer portal
- Need to publish a backend (Function / App Service / Cosmos DB) through a managed gateway
- Apply rate-limit / quota / JWT / subscription-key policies

### SHOULD NOT Use When
- Functions backend CRUD → delegate to: `azure-function-ops`
- App Service backend CRUD → delegate to: `azure-appservice-ops`
- L7 routing / WAF in front of APIM → delegate to: `azure-appgateway-ops` or `azure-frontdoor-ops`
- Monitoring / alerts / diagnostics on APIM → delegate to: `azure-monitor-ops`
- Cosmos DB backend CRUD → delegate to: `azure-cosmos-ops`
- Billing only → delegate to: `azure-cost-ops`
- VNet / subnet for APIM internal mode → delegate to: `azure-network-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` / `_TENANT_ID` / `_CLIENT_ID` / `_CLIENT_SECRET` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure location (e.g., eastus) |
| `{{user.apim_name}}` | User input | APIM service name (globally unique) |
| `{{user.apim_sku}}` | User input | Consumption / Developer / Basic / Standard / Premium / Isolated |
| `{{user.publisher_email}}` / `{{user.publisher_name}}` | User input | Required by `az apim create` |
| `{{user.api_id}}` / `{{user.product_id}}` / `{{user.subscription_id}}` | User input | Resource identifiers (`sid` for subscription) |
| `{{output.apim_id}}` | Last response | Parse `.id` from CLI/SDK output |
| `{{output.primary_key}}` / `{{output.secondary_key}}` | Last response | Subscription keys — **sensitive, never print** |

## Execution Flow Pattern

```
Pre-flight → Execute (CLI primary / SDK fallback) → Validate → Recover
```

### Operation: Create APIM Instance (LRO)

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
<!-- 通用 5 步 Pre-flight 见 [azure-cli-conventions.md#pre-flight-checks-canonical-all-azure--ops-share](../../azure-skill-generator/references/azure-cli-conventions.md#pre-flight-checks-canonical-all-azure--ops-share) -->
| Name globally unique | `az apim check-name -n {{user.apim_name}} --output json` | HALT; pick different name |
| Publisher email/name | Ask user; non-empty | HALT |

#### Execute — Azure CLI (Primary)
```bash
az apim create \
  --name "{{user.apim_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --publisher-email "{{user.publisher_email}}" \
  --publisher-name "{{user.publisher_name}}" \
  --sku-name "{{user.apim_sku}}" \
  --sku-capacity 1 \
  --output json
```

#### Execute — Azure SDK (Fallback)
See `references/integration.md#create-apim-service-long-running`. The key call: `client.api_management_service.begin_create_or_update(...).result()` (LRO 5-45 min for non-Consumption).

#### Validate
```bash
# provisioningState must be "Succeeded"
az apim show --name "{{user.apim_name}}" --resource-group "{{user.resource_group}}" --output json
```

#### Recover
| Error | Action |
|-------|--------|
| `InvalidParameter` / `InvalidPublisherEmail` | Fix args; retry once |
| `ResourceNameInvalid` / `CheckNameNotAvailable` | HALT; name conflict |
| `QuotaExceeded` | HALT; request quota increase |
| `ThrottlingException` (429) | Backoff, retry 3x |
| `5xx Internal` | Retry 3x, then HALT |

## Key Operations — CLI vs SDK Coverage

Full per-operation CLI/SDK matrix: see `references/integration.md#cli-vs-sdk-coverage-summary`. Highlights:

> **CLI gap**: `az apim` does **not** expose subscription, API policy, product policy, or global policy commands. These operations go through **Azure SDK (Python)**. `--output json` still required on every CLI command elsewhere. SDK code samples in `references/integration.md`.

## Destructive Operations — Safety Gate

MUST obtain explicit user confirmation before any delete. User must type the exact resource name.

```bash
az apim show --name "{{user.apim_name}}" --resource-group "{{user.resource_group}}" --output json
# User must type exact name to confirm
az apim delete --name "{{user.apim_name}}" --resource-group "{{user.resource_group}}" --yes
```

**Subscription key regeneration** and **Policy overwrite** also require explicit confirmation: regenerating primary key invalidates existing clients; overwriting policy immediately affects all gateway traffic.

## Quality Gate

GCL **required**, `max_iterations=2`. See `AGENTS.md §3–§8`.

| Rubric | Prompt templates |
|--------|------------------|
| [references/rubric.md](references/rubric.md) | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE APIM / API / Product / Subscription → **required**; Safety=0 → ABORT; traffic impact warning
- REGENERATE subscription key → **required**; Safety=0 if any key visible in trace
- POLICY create/overwrite → **required**; warning: immediate traffic impact; Policy XML never leaked in trace
- CREATE APIM / LIST / SHOW → recommended

### Subscription Key & Policy XML Security

Subscription keys are sensitive credentials; Policy XML may contain connection strings. The GCL trace MUST NOT contain raw key values or `<set-*>` policy `value=` attributes. If detected, **safety=0 → ABORT**.

## L4 Auto-Feedback Loop

For autonomous operation on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-apim-ops \
  --operation apim_create \
  --command "az apim create --name {{user.apim_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"provisioningState": "Succeeded"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (apim_create): auto-feedback loop active
- **Risky operations** (delete): always bypass loop and require explicit human confirmation
- Healing policy: see [`scripts/self_healing/apim_heal.json`](../../scripts/self_healing/apim_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)
