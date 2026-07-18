---
name: azure-function-ops
description: >-
  Use when operating Azure Functions resources (Function App, hosting plan) via Azure CLI or Azure SDK;
  user mentions "Azure Functions", "Function App", "serverless", "function hosting plan",
  or function deployment/scale/delete operations.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-07-11"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Functions Operations Skill

## Overview

Azure Functions is a serverless compute service. A **Function App** is the management/execution unit (built on App Service); a **hosting plan** (Consumption / Premium / Dedicated) controls scale and billing. This `SKILL.md` is the slim entrypoint — keep triggers, scope, flow, safety gates, and links here; move detailed commands, SDK snippets, and RCA rules into `references/`.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure Functions", "Function App", "serverless function", "function hosting plan"
- Task involves CRUD on **Function App** / **hosting plan** (create, show, deploy, restart, delete, list, scale); keywords: functionapp, consumption/premium plan, deployment slot, function keys
- Deploying code/zip, managing app settings or function keys

### SHOULD NOT Use When
- Generic App Service web apps → delegate to: `azure-appservice-ops`
- Kubernetes-based functions (KEDA) → delegate to: `azure-aks-ops`
- Container image build/push → delegate to: `azure-acr-ops`
- Trigger source provisioning (Queue/Event Hub/Service Bus/Blob) → delegate to the storage/event service skill (this skill only configures the binding)
- Billing only → delegate to: `azure-cost-ops`; RBAC/IAM only → delegate to the RBAC skill when available

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` / `{{env.AZURE_TENANT_ID}}` / `{{env.AZURE_CLIENT_ID}}` / `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZUREWEBJOBS_STORAGE}}` | Runtime env | Storage connection string for `AzureWebJobsStorage`; NEVER ask user |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure location (e.g., eastus) |
| `{{user.function_app_name}}` | User input | Globally-unique DNS name; ask once |
| `{{user.plan_name}}` | User input | Existing Premium/Dedicated plan name |
| `{{user.storage_account}}` | User input | Required for Consumption plan (runtime storage) |
| `{{user.runtime}}` | User input | dotnet, node, python, java, powershell |
| `{{user.zip_path}}` | User input | Local zip package path for deploy |
| `{{user.assignee_id}}` | User input | Principal/SP object ID for RBAC assignment |
| `{{output.plan_id}}` | From plan query | Parse `id` from plan response |
| `{{output.function_app_id}}` | Last API response | Parse `.id` from Azure CLI output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**. CLI is primary; SDK fallback (azure-mgmt-web) for every operation in `references/integration.md` and `references/cli-reference.md`.

### Operation: Create Function App

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI / Credentials / Subscription | `az --version`; `az account show`; `az account list` | Install CLI / configure env / suggest sub |
| Resource Group exists | `az group show --name {{user.resource_group}}` | Create or suggest existing |
| Location valid | `az account list-locations --output json` | Suggest valid location |
| Storage account (Consumption only) | `az storage account show --name {{user.storage_account}} --resource-group {{user.resource_group}}` | HALT; storage required |

#### Execute — Azure CLI (Primary)
```bash
# Create Consumption plan + Function App in one step (requires storage account)
az functionapp create \
  --name "{{user.function_app_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --storage-account "{{user.storage_account}}" \
  --runtime "{{user.runtime}}" \
  --consumption-plan-location "{{user.location}}" \
  --output json

# Create Function App on an existing (Premium/Dedicated) plan
az functionapp create \
  --name "{{user.function_app_name}}" \
  --resource-group "{{user.resource_group}}" \
  --plan "{{user.plan_name}}" \
  --runtime "{{user.runtime}}" \
  --output json
```
# SDK fallback (azure-mgmt-web, kind=functionapp): references/integration.md
# Validate: `az functionapp show ...` → state=="Running" & default_host_name populated

#### Recover
HALT on `QuotaExceeded` / `AccessDenied`; backoff-retry `Throttling`/`5xx` ≤3×; fix args and retry once on `InvalidParameter` / `NameUnavailable`. Full table: references/troubleshooting.md.

### Operation: Deploy / Restart / Show / List

Slim entrypoints only — full CLI + Azure SDK (azure-mgmt-web) snippets live in **`references/cli-reference.md`**.

- **Deploy Code**: `az functionapp deployment source config-zip ...` (CLI) / `client.web_apps.create_one_deploy_operation(...)` (SDK)
- **Restart**: `az functionapp restart ...` (CLI) / `client.web_apps.restart(...)` (SDK)
- **Show**: `az functionapp show ...` (CLI) / `client.web_apps.get(...)` (SDK)
- **List**: `az functionapp list ...` (CLI) / `client.web_apps.list_by_resource_group(...)` (SDK)

### Operation: Delete Function App

**Safety Gate**: MUST obtain explicit user confirmation before deletion. All functions, slots, and app settings are permanently lost (storage account and plan are retained).

```bash
# 1. Show before deletion
az functionapp show --name "{{user.function_app_name}}" --resource-group "{{user.resource_group}}" --output json

# 2. Request confirmation (user must type exact Function App name), then proceed:
az functionapp delete \
  --name "{{user.function_app_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```
# SDK fallback (delete): references/integration.md

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate (spec: `AGENTS.md §3–§8`):

| Parameter | Value |
|-----------|-------|
| GCL | **required** (max_iterations=2) |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE (`az functionapp delete`) → **required**; Safety=0 → ABORT
- CREATE (`az functionapp create`) → **required**; validate pre-flight + name uniqueness
- DEPLOY (`az functionapp deployment source config-zip`) → recommended; verify non-destructive to slots
- RESTART / SHOW / LIST → optional

## Reference Files

- [Core Concepts](references/core-concepts.md) · [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md) · [CLI & SDK Reference](references/cli-reference.md)
- [Rubric](references/rubric.md) · [Prompt Templates](references/prompt-templates.md)



