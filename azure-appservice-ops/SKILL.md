---
name: azure-appservice-ops
description: >-
  Use when operating Azure App Service resources via Azure CLI or Azure SDK;
  user mentions "App Service", "Web App", "App Service Plan", deployment slots, app settings, or scale-out.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-06-09"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure App Service Operations Skill

## Overview

Azure App Service hosts web apps, APIs, and background web workloads on managed compute. Use this skill for App Service Plans, Web Apps, slots, app settings, scale, restart/stop/start, logs, diagnostics, and safe deletion.

## Trigger & Scope

### SHOULD Use When
- User mentions "App Service", "Web App", `azurewebsites.net`, App Service Plan, deployment slot, app settings, or runtime stack
- Task involves CRUD on **Web Apps** or **App Service Plans**
- Task involves start/stop/restart, scale up/out, logs, diagnostics, VNet integration, or slot swap
- Task involves runtime configuration such as Python/Node/.NET/Java settings

### SHOULD NOT Use When
- VM lifecycle or SSH/RDP server control → delegate to: `azure-vm-ops`
- AKS / Kubernetes workloads → delegate to: `azure-aks-ops`
- Container registry/image pull RCA → delegate to: `azure-acr-ops`
- Front Door/global edge routing → delegate to: `azure-frontdoor-ops`
- Application Gateway/WAF ingress → delegate to: `azure-appgateway-ops`
- Database creation or schema work → delegate to database-specific skill
- Key Vault secret lifecycle → delegate to: `azure-keyvault-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure Location (e.g., eastus); validate |
| `{{user.plan_name}}` | User input | App Service Plan name |
| `{{user.webapp_name}}` | User input | Globally unique Web App name |
| `{{user.runtime}}` | User input | Runtime, e.g., `PYTHON:3.11`, `NODE:20-lts`, `DOTNETCORE:8.0` |
| `{{user.sku}}` | User input | Plan SKU, e.g., B1, P1v3 |
| `{{output.plan_id}}` | Last API response | Parse: `.id` from plan output |
| `{{output.webapp_id}}` | Last API response | Parse: `.id` from web app output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**. Use Azure CLI first. If CLI fails after up to 3 retries with backoff, use Azure SDK for Python fallback. Poll LROs every 10 seconds for up to 15 minutes. See [Integration Setup](references/integration.md) for SDK client setup and RBAC.

### Operation: Create App Service Plan and Web App

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
<!-- 通用 5 步 Pre-flight 见 [azure-cli-conventions.md#pre-flight-checks-canonical-all-azure--ops-share](../../azure-skill-generator/references/azure-cli-conventions.md#pre-flight-checks-canonical-all-azure--ops-share) -->
| Web App name available | `az webapp list --query` | Ask for globally unique name |
| SKU supports feature | Check plan SKU before slots/VNet/custom domains | HALT or suggest SKU |

#### Execute
- CLI primary: `az appservice plan create ... --output json`, then `az webapp create ... --output json`
- SDK fallback: `WebSiteManagementClient.app_service_plans.begin_create_or_update(...)`, then `web_apps.begin_create_or_update(...)`
- Required fields: Resource Group, Location, plan name, Web App name, SKU, OS, runtime

#### Validate
- Show Web App and confirm `state` plus `serverFarmId`
- Show App Service Plan and confirm SKU/worker count
- Capture full resource IDs in `{{output.plan_id}}` and `{{output.webapp_id}}`

#### Recover
| Error | Action |
|-------|--------|
| WebAppNameUnavailable | HALT; ask for unique app name |
| InvalidSku | HALT; choose supported SKU for Location/features |
| QuotaExceeded | HALT; request quota increase or choose another Location/SKU |
| AuthorizationFailed | HALT; require Website Contributor/Contributor |
| Throttling (429) | Backoff, retry up to 3x |
| 5xx Internal | Retry up to 3x, then HALT |

### Operation: Configure Web App

Use `az webapp config appsettings set|list`, `az webapp config set`, and `az webapp connection-string set|list` as CLI primary; use `WebSiteManagementClient.web_apps.update_application_settings(...)` and `update_configuration(...)` as SDK fallback. Treat values for secret-like keys as sensitive and mask them in all traces.

### Operation: Lifecycle, Scale, and Slots

Use `az webapp start|stop|restart`, `az appservice plan update`, and `az webapp deployment slot ... --output json` as CLI primary; use `WebSiteManagementClient.web_apps.start|stop|restart(...)`, `app_service_plans.begin_create_or_update(...)`, and slot APIs as SDK fallback. STOP, production restart, SKU downgrade, worker-count reduction, and slot swap require impact warning and exact-name confirmation.

### Operation: Delete Web App or App Service Plan

**Safety Gate**: MUST obtain explicit human confirmation before stop, delete, scale-to-0-equivalent changes, or slot swap. For Web App deletion, show app state, hostname, plan, slots, and recent deployment metadata. For plan deletion, list every app attached to the plan. User must type the exact app or plan name.

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate. See `AGENTS.md §3–§8`.

| Parameter | Value |
|-----------|-------|
| GCL | **required** |
| max_iterations | 2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE web app / plan → **required**; traffic/data impact warning + Safety=0 → ABORT
- STOP web app / restart production app → **required**; availability impact warning
- Slot swap → **required**; production routing impact and source/target confirmation
- Scale down / SKU downgrade → **required**; capacity and feature-loss warning
- App settings update with secret-like keys → **required**; secret masking check
- CREATE / SHOW / LIST / LOGS → recommended

## L4 Auto-Feedback Loop

For autonomous operation on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-appservice-ops \
  --operation webapp_create \
  --command "az webapp create --name {{user.webapp_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"state": "Running"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (webapp_create): auto-feedback loop active
- **Risky operations** (delete): always bypass loop and require explicit human confirmation
- Healing policy: see [`scripts/self_healing/appservice_heal.json`](../../scripts/self_healing/appservice_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [Azure CLI Web App Reference](https://docs.microsoft.com/cli/azure/webapp)
- [Azure SDK Web Module](https://docs.microsoft.com/python/api/azure-mgmt-web/)


> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
