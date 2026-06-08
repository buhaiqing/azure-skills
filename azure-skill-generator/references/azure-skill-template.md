---
name: azure-[service-name]-ops
description: >-
  Use when operating Azure [Service Name] resources via Azure CLI or Azure SDK;
  user mentions [Service Name], [Service Alias], or [Resource Type].
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK (Python 3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-05-10"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure [Service Name] Operations Skill

## Overview

Azure [Service Name] provides [brief description]. This `SKILL.md` is the slim entrypoint (~100-150 lines): keep triggers, scope, flow, safety gates, and links here; move detailed commands, SDK snippets, RCA rules, AIOps playbooks, and design detail into `references/`.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure [Service Name]" or "[Service Alias]"
- Task involves CRUD on **[Resource Type]** (create, show, update, delete, list)
- Keywords: [keyword1], [keyword2], [keyword3]

### SHOULD NOT Use When
- Billing only → delegate to: `azure-cost-ops`
- RBAC/IAM only → delegate to: `azure-rbac-ops`
- Related service → delegate to: `azure-[other]-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure region (e.g., eastus) |
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

### Operation: Create [Resource]

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show` | HALT; configure env |
| Subscription valid | `az account list --output json` | Suggest valid subscription |
| Resource Group exists | `az group show --name {{user.resource_group}}` | Create or suggest existing |
| Location valid | `az account list-locations --output json` | Suggest valid location |
| Quota | Check Azure quotas | HALT; request increase |

#### Execute — Azure CLI (Primary)
```bash
az [service] [resource] create \
  --name "{{user.resource_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --output json
```

#### Execute — Azure SDK (Fallback)
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.[service] import [ServiceMgmtClient]

credential = DefaultAzureCredential()
client = [ServiceMgmtClient](
    credential,
    subscription_id='{{env.AZURE_SUBSCRIPTION_ID}}'
)

response = client.[resources].begin_create_or_update(
    resource_group_name='{{user.resource_group}}',
    resource_name='{{user.resource_name}}',
    parameters={
        'location': '{{user.location}}',
        # Additional parameters per Azure REST API docs
    }
).result()
```

#### Validate
Poll until terminal state (succeeded/failed) with max wait.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| QuotaExceeded | HALT |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |

### Operation: Delete [Resource]

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

```bash
# Show resource before deletion
az [service] [resource] show --name "{{user.resource_name}}" --resource-group "{{user.resource_group}}" --output json

# Request confirmation
# User must type exact resource name to confirm
```

## Reference Files

- [Azure CLI Usage](references/azure-cli-usage.md)
- [Azure SDK Usage](references/azure-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)