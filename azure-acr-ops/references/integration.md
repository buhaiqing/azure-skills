# Azure Container Registry Integration and Commands

## Required Tools

```bash
az version --output json
az account show --output json
az provider show --namespace Microsoft.ContainerRegistry --output json
```

If `Microsoft.ContainerRegistry` is not registered, HALT and ask for approval before registration:

```bash
az provider register --namespace Microsoft.ContainerRegistry --output json
```

## Required RBAC

| Operation | Minimum Role |
|-----------|--------------|
| Read registry metadata | Reader |
| Pull images | AcrPull |
| Push/import/delete images | AcrPush or AcrDelete as appropriate |
| Registry create/update/delete | Contributor or AcrPush plus resource permissions depending on action |
| Network/private endpoint changes | Network Contributor on network scope + registry permissions |
| Role assignment changes | User Access Administrator or Owner; prefer delegate to `azure-audit-ops` |

Do not ask for registry passwords or service principal secrets.

## Pre-flight Checklist

```bash
az account show --output json
az group show --name "{{user.resource_group}}" --output json
az account list-locations --query "[?name=='{{user.location}}']" --output json
az provider show --namespace Microsoft.ContainerRegistry --query "registrationState" --output json
```

For existing registry:

```bash
az acr show \
  --name "{{user.registry_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

## Azure CLI Primary Path

### Registry List and Show

```bash
az acr list \
  --resource-group "{{user.resource_group}}" \
  --output json

az acr show \
  --name "{{user.registry_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,loginServer:loginServer,sku:sku.name,state:provisioningState,admin:adminUserEnabled,publicNetworkAccess:publicNetworkAccess}" \
  --output json
```

### Create Registry

```bash
az acr create \
  --name "{{user.registry_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --sku "{{user.sku}}" \
  --admin-enabled false \
  --output json
```

### Repository / Tag / Manifest Inspect

```bash
az acr repository list \
  --name "{{user.registry_name}}" \
  --output json

az acr repository show-tags \
  --name "{{user.registry_name}}" \
  --repository "{{user.repository}}" \
  --detail \
  --output json

az acr manifest list-metadata \
  --registry "{{user.registry_name}}" \
  --name "{{user.repository}}" \
  --output json
```

### Import Image

```bash
az acr import \
  --name "{{user.registry_name}}" \
  --source "{{user.source_image}}" \
  --image "{{user.repository}}:{{user.tag}}" \
  --output json
```

If importing over a production tag, require confirmation.

### Delete Image Artifacts

```bash
az acr repository show-tags \
  --name "{{user.registry_name}}" \
  --repository "{{user.repository}}" \
  --detail \
  --output json

# After explicit confirmation:
az acr repository delete \
  --name "{{user.registry_name}}" \
  --image "{{user.repository}}:{{user.tag}}" \
  --yes \
  --output json
```

Digest deletion must target `{{user.repository}}@{{user.digest}}` and requires confirmation.

### Network and Admin State

```bash
az acr show \
  --name "{{user.registry_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{publicNetworkAccess:publicNetworkAccess,networkRuleSet:networkRuleSet,privateEndpointConnections:privateEndpointConnections,adminUserEnabled:adminUserEnabled}" \
  --output json
```

Enable admin user only with explicit approval and a rotation plan.

### Delete Registry

```bash
az acr show \
  --name "{{user.registry_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# After explicit confirmation:
az acr delete \
  --name "{{user.registry_name}}" \
  --resource-group "{{user.resource_group}}" \
  --yes \
  --output json
```

## Azure SDK Fallback

Use SDK only after CLI transient failures are retried up to 3x.

```python
import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerregistry import ContainerRegistryManagementClient

client = ContainerRegistryManagementClient(DefaultAzureCredential(), os.environ["AZURE_SUBSCRIPTION_ID"])
# client bootstrap: see ../../../azure-skill-generator/references/azure-sdk-usage.md#common-client-bootstrap

registry = client.registries.get(
    resource_group_name="{{user.resource_group}}",
    registry_name="{{user.registry_name}}",
)
print(registry.id)
```

Create/update pattern:

```python
poller = client.registries.begin_create(
    resource_group_name="{{user.resource_group}}",
    registry_name="{{user.registry_name}}",
    registry={
        "location": "{{user.location}}",
        "sku": {"name": "{{user.sku}}"},
        "admin_user_enabled": False,
    },
)
result = poller.result(timeout=1800)
print(result.id)
```

Delete pattern:

```python
poller = client.registries.begin_delete(
    resource_group_name="{{user.resource_group}}",
    registry_name="{{user.registry_name}}",
)
poller.result(timeout=1800)
```

## Polling

| Operation | Poll Interval | Max Wait |
|-----------|---------------|----------|
| create/update/delete registry | 30s | 30m |
| import image | 15s | 30m |
| repository/tag delete | 15s | 10m |
| network update | 30s | 20m |

On timeout, do not repeat mutation. Re-read state and report uncertainty.
