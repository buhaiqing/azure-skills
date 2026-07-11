# Integration Setup (Azure Functions)

> SDK 方法名经 `azure-mgmt-web` 实测校验（11.0.0：`dir(WebSiteManagementClient.web_apps)`），无编造方法名。

## Environment Setup

Azure Functions operations require Azure CLI and optionally Azure SDK for Python (fallback).

### Install Azure CLI (One-time per machine)

```bash
# macOS
brew install azure-cli

# Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
# Download from: https://aka.ms/installazurecliwindows
```

### Install Azure SDK for Python (Fallback)

```bash
pip install azure-identity azure-mgmt-resource
# Functions/Function App lives under the Web (App Service) management plane
pip install azure-mgmt-web

python -c "from azure.mgmt.web import WebSiteManagementClient; print('Azure Web SDK OK')"
```

## Credential Configuration

### Method A: Service Principal (Recommended for Automation)

```bash
az ad sp create-for-rbac \
  --name "my-function-automation-sp" \
  --role "Contributor" \
  --scopes "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --output json
```

Store credentials as runtime environment variables (NEVER commit; use `{{env.*}}` placeholders only). The SDK reads these directly from the process environment at runtime (e.g. `os.environ['AZURE_SUBSCRIPTION_ID']`), so no shell re-export is required — just ensure the variables are present in the environment before running the agent.

> Never paste a real secret into a command or file. If a variable is unset, fail closed.

### Method B: Azure CLI Login (Interactive)

```bash
az login
az account set --subscription "{{env.AZURE_SUBSCRIPTION_ID}}"
az account show --output json
```

## Prerequisites

### Storage Account (Consumption Plan Required)

```bash
# Verify storage account exists (Consumption plan needs it)
az storage account show --name "{{user.storage_account}}" --resource-group "{{user.resource_group}}" --output json
# If missing, delegate creation to azure-blobstorage-ops
```

### Hosting Plan (Premium / Dedicated)

```bash
# List existing plans to reuse
az functionapp plan list --resource-group "{{user.resource_group}}" --output json
# Plan creation is delegated to azure-appservice-ops (App Service plan CRUD)
```

## Python SDK Usage (Fallback)

### Authenticate and Create Client

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.web import WebSiteManagementClient
import os

credential = DefaultAzureCredential()
client = WebSiteManagementClient(
    credential,
    subscription_id=os.environ['AZURE_SUBSCRIPTION_ID']
)
```

> **LRO polling strategy**: Among the methods used here, only `begin_create_or_update(...)` is a
> long-running operation (LRO) — call it with `.result()` to block until completion (or `.wait()`)
> and enforce your own timeout. `restart(...)`, `delete(...)`, `get(...)`,
> `list_by_resource_group(...)`, and `create_one_deploy_operation(...)` are **synchronous** calls
> and return immediately — do NOT poll or call `.wait()`/`.result()` on them.

### Create Function App (kind=functionapp)

```python
# runtime -> site_config mapping; do NOT hardcode python_version.
# The runtime is supplied by {{user.runtime}} (dotnet/node/python/java/powershell).
runtime = '{{user.runtime}}'

site = client.web_apps.begin_create_or_update(
    resource_group_name='{{user.resource_group}}',
    name='{{user.function_app_name}}',
    site_envelope={
        'location': '{{user.location}}',
        'kind': 'functionapp',
        'server_farm_id': '{{output.plan_id}}',
        'site_config': {'linux_fx_version': f'{runtime}|3.11'} if runtime == 'python' else {},
    }
).result()
```

### Show / Deploy / Restart / List (Fallback)

Full snippets (`get`, `restart`, `list_by_resource_group`, `create_one_deploy_operation`) live in
**`references/cli-reference.md`**. Summary signatures:

```python
app = client.web_apps.get('{{user.resource_group}}', '{{user.function_app_name}}')
client.web_apps.restart('{{user.resource_group}}', '{{user.function_app_name}}')
apps = client.web_apps.list_by_resource_group('{{user.resource_group}}')
```

### Delete (Destructive — requires explicit confirmation, see SKILL.md)

`delete(...)` is a synchronous call (not an LRO) — it returns an `AzureOperationPoller`-free result
and requires no `.wait()`.

```python
client.web_apps.delete(
    resource_group_name='{{user.resource_group}}',
    name='{{user.function_app_name}}',
)
```

## App Settings (Runtime Configuration)

```bash
# Set worker runtime + storage connection string
az functionapp config appsettings set \
  --name "{{user.function_app_name}}" \
  --resource-group "{{user.resource_group}}" \
  --settings "FUNCTIONS_WORKER_RUNTIME={{user.runtime}}" "AzureWebJobsStorage={{env.AZUREWEBJOBS_STORAGE}}" \
  --output json

# List settings (verify, do NOT print secret values to log)
az functionapp config appsettings list --name "{{user.function_app_name}}" --resource-group "{{user.resource_group}}" --output json
```

> `AzureWebJobsStorage` must point to the storage connection string. Use the
> `{{env.AZUREWEBJOBS_STORAGE}}` environment variable — never inline the literal connection string.

## RBAC Roles for Functions

| Role | Permissions |
|------|-------------|
| **Contributor** | Full Function App management |
| **Website Contributor** | Manage web/function apps (no RBAC) |
| **Reader** | Read-only |

```bash
az role assignment create \
  --assignee "{{user.assignee_id}}" \
  --role "Website Contributor" \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Web/sites/{{user.function_app_name}}"
```

## Common Azure Locations for Functions

| Location | Display Name |
|----------|--------------|
| eastus | East US |
| eastus2 | East US 2 |
| westus2 | West US 2 |
| westeurope | West Europe |
| northeurope | North Europe |
| southeastasia | Southeast Asia |

## Quick Reference Commands

```bash
# Show app
az functionapp show --name myFuncApp --resource-group myRG

# Restart
az functionapp restart --name myFuncApp --resource-group myRG

# Tail logs
az functionapp log tail --name myFuncApp --resource-group myRG

# List keys (HTTP trigger auth)
az functionapp keys list --name myFuncApp --resource-group myRG
```
