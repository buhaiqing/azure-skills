# SDK 方法名经实测校验

> **SDK 方法名经实测校验**：`azure-mgmt-containerinstance==10.1.0` 已通过 `pip install` 安装并 introspect 确认以下方法真实存在（非凭记忆编造）：
> - `client.container_groups.begin_create_or_update(rg, cg_name, container_group)` → LROPoller
> - `client.container_groups.begin_delete(rg, cg_name)` → LROPoller
> - `client.container_groups.begin_restart(rg, cg_name)` → LROPoller
> - `client.container_groups.begin_start(rg, cg_name)` → LROPoller
> - `client.container_groups.get(rg, cg_name)` → ContainerGroup
> - `client.container_groups.list()` / `list_by_resource_group(rg)` → Iterable
> - `client.container_groups.stop(rg, cg_name)` → None（同步，非 begin_*）
> - `client.containers.list_logs(rg, cg_name, container_name, tail=..., timestamps=...)` → Logs
>
> **重要更正**：日志方法位于 `client.containers`，**不是** `client.container_groups.list_logs`。

# Integration Setup (Azure Container Instances)

## Environment Setup

ACI ops require Azure CLI, Azure SDK, and (for private images) registry credentials.

### Install Azure CLI (one-time)
```bash
# macOS
brew install azure-cli
# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Install Azure SDK for Python
```bash
pip install azure-identity azure-mgmt-containerinstance
python -c "from azure.mgmt.containerinstance import ContainerInstanceManagementClient; print('ACI SDK OK')"
```

## Credential Configuration

### Method A: Service Principal (automation)
```bash
az ad sp create-for-rbac --name "aci-automation-sp" --role "Contributor" \
  --scopes "/subscriptions/{{subscription-id}}" --output json
export AZURE_SUBSCRIPTION_ID="{{sub-id}}"
export AZURE_TENANT_ID="{{tenant-id}}"
export AZURE_CLIENT_ID="{{app-id}}"
export AZURE_CLIENT_SECRET="{{password}}"
```

### Method B: Azure CLI login (interactive)
```bash
az login
az account set --subscription "{{subscription-id}}"
az account show --output json
```

## Pre-flight Checks

```bash
az --version
az account show
az group show --name "{{user.resource_group}}"
az account list-locations --query "[].name" --output json
az container list-usage --location "{{user.location}}" --output json
```

## Private Registry Auth (delegate registry ops to azure-acr-ops)

```bash
# ACI pulls with provided creds (password from env, never pasted)
az container create \
  --name "{{user.container_group}}" \
  --resource-group "{{user.resource_group}}" \
  --image "{{user.registry_image}}" \
  --registry-login-server "{{user.registry_login_server}}" \
  --registry-username "{{user.registry_username}}" \
  --registry-password "{{env.REGISTRY_PASSWORD}}" \
  --output json
```

For ACR managed-identity pulls, role assignment and registry auth → `azure-acr-ops`.

## Python SDK Usage

### Client init
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
import os

client = ContainerInstanceManagementClient(
    DefaultAzureCredential(),
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)
```

### Create
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
import os

credential = DefaultAzureCredential()
client = ContainerInstanceManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

poller = client.container_groups.begin_create_or_update(
    resource_group_name='{{user.resource_group}}',
    container_group_name='{{user.container_group}}',
    container_group={
        'location': '{{user.location}}',
        'containers': [{
            'name': '{{user.container_name}}',
            'image': '{{user.image}}',
            'resources': {'requests': {'cpu': 1.0, 'memory_in_gb': 1.5}}
        }],
        'restart_policy': 'OnFailure',
        'os_type': 'Linux'
    }
).result()
```

### Show / List / Restart / Delete / Stop / Logs
```python
cg = client.container_groups.get('{{rg}}', '{{cg}}')
for g in client.container_groups.list_by_resource_group('{{rg}}'):
    print(g.name)
client.container_groups.begin_restart('{{rg}}', '{{cg}}').wait()
client.container_groups.begin_delete('{{rg}}', '{{cg}}').wait()
client.container_groups.stop('{{rg}}', '{{cg}}')  # synchronous
logs = client.containers.list_logs('{{rg}}', '{{cg}}', '{{container}}', tail=100)
print(logs.content)
```

## RBAC Roles

| Role | Permissions |
|------|-------------|
| Contributor | Full ACI management |
| Container Instance Contributor | ACI operations (no RBAC) |
| AcrPull | Pull from ACR (assign to ACI identity) → `azure-acr-ops` |

```bash
az role assignment create \
  --assignee "{{user-or-sp-id}}" \
  --role "Container Instance Contributor" \
  --scope "/subscriptions/{{sub}}/resourceGroups/{{rg}}/providers/Microsoft.ContainerInstance/containerGroups/{{cg}}"
```

## Quick Reference

```bash
az container create --name cg --resource-group rg --image nginx --cpu 1 --memory 1.5 --restart-policy OnFailure
az container show --name cg --resource-group rg --output json
az container list --resource-group rg --output json
az container restart --name cg --resource-group rg
az container logs --name cg --resource-group rg --container-name cg
az container delete --name cg --resource-group rg --yes
```

## pyproject.toml
```toml
[project]
name = "azure-aci-ops"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "azure-identity>=1.10.0",
    "azure-mgmt-containerinstance>=10.0.0",
]
```
