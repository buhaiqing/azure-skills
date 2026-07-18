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

认证四件套 `{{env.AZURE_SUBSCRIPTION_ID/TENANT_ID/CLIENT_ID/SECRET}}`（NEVER ask user; fail if unset）为规范常量，详见 [azure-cli-conventions.md §Credential Sources](../../azure-skill-generator/references/azure-cli-conventions.md)。SKILL.md 仅声明业务占位符：

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure region (e.g., eastus) |
| `{{user.resource_name}}` | User input | Ask once; reuse |
| `{{output.resource_id}}` | Last API response | Parse per Azure REST API docs |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**. Pre-flight 五步检查（CLI/credentials/subscription/Resource Group/Location）为通用骨架，详见 [azure-cli-conventions.md §Common Pitfalls](../../azure-skill-generator/references/azure-cli-conventions.md)；重试与 429/5xx 策略见同文件 §Retry Strategy。SKILL.md 只描述本服务的偏差。

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create [Resource]

#### Pre-flight
通用五步见约定文档；本服务额外检查：

| Check | Method | On Failure |
|-------|--------|------------|
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