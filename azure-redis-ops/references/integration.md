# Azure Redis Integration and Commands

## Required Tools

```bash
az version --output json
az account show --output json
az provider show --namespace Microsoft.Cache --output json
```

If `Microsoft.Cache` is not registered, HALT and ask for approval before registration:

```bash
az provider register --namespace Microsoft.Cache --output json
```

## Required RBAC

| Operation | Minimum Role |
|-----------|--------------|
| Read/show/list/metrics | Reader + Monitoring Reader |
| Create/update/scale/reboot/key rotation/delete | Contributor or Redis Cache Contributor |
| Private endpoint connection approval | Network Contributor on network scope + resource permissions |
| Role assignment changes | User Access Administrator or Owner; prefer delegate to `azure-audit-ops` |

Do not ask for secrets. Use environment credentials through Azure CLI or `DefaultAzureCredential`.

## Pre-flight Checklist

```bash
az account show --output json
az group show --name "{{user.resource_group}}" --output json
az account list-locations --query "[?name=='{{user.location}}']" --output json
az provider show --namespace Microsoft.Cache --query "registrationState" --output json
```

For existing resources:

```bash
az redis show \
  --name "{{user.redis_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

For metric names:

```bash
az monitor metrics list-definitions \
  --resource "{{output.redis_id}}" \
  --output json
```

## Azure CLI Primary Path

### List and Show

```bash
az redis list \
  --resource-group "{{user.resource_group}}" \
  --output json

az redis show \
  --name "{{user.redis_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### Create Standard/Premium Cache

```bash
az redis create \
  --name "{{user.redis_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --sku "{{user.sku}}" \
  --vm-size "{{user.capacity}}" \
  --enable-non-ssl-port false \
  --output json
```

Validate:

```bash
az redis show \
  --name "{{user.redis_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id, state:provisioningState, host:hostName, sslPort:sslPort}" \
  --output json
```

### Update Configuration

```bash
az redis update \
  --name "{{user.redis_name}}" \
  --resource-group "{{user.resource_group}}" \
  --set redisConfiguration.maxmemory-policy="{{user.eviction_policy}}" \
  --output json
```

Never disable TLS or enable the non-SSL port without explicit confirmation.

### Scale

Scale up after confirming SKU/capacity support:

```bash
az redis update \
  --name "{{user.redis_name}}" \
  --resource-group "{{user.resource_group}}" \
  --sku "{{user.sku}}" \
  --vm-size "{{user.capacity}}" \
  --output json
```

Scale down requires explicit confirmation and rollback notes.

### Reboot

```bash
az redis force-reboot \
  --name "{{user.redis_name}}" \
  --resource-group "{{user.resource_group}}" \
  --reboot-type AllNodes \
  --output json
```

Requires confirmation. Capture pre/post metrics and expected client impact.

### Regenerate Keys

```bash
az redis regenerate-keys \
  --name "{{user.redis_name}}" \
  --resource-group "{{user.resource_group}}" \
  --key-type Primary \
  --output json
```

Requires confirmation and client rotation plan. Prefer secondary-key rotation first.

### Firewall Rules

```bash
az redis firewall-rules list \
  --name "{{user.redis_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az redis firewall-rules create \
  --name "{{user.rule_name}}" \
  --redis-name "{{user.redis_name}}" \
  --resource-group "{{user.resource_group}}" \
  --start-ip "{{user.start_ip}}" \
  --end-ip "{{user.end_ip}}" \
  --output json
```

Broad ranges such as `0.0.0.0-255.255.255.255` require refusal unless a documented emergency approval exists.

### Delete

```bash
az redis show \
  --name "{{user.redis_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# After explicit confirmation:
az redis delete \
  --name "{{user.redis_name}}" \
  --resource-group "{{user.resource_group}}" \
  --yes \
  --output json
```

## Azure SDK Fallback

Use SDK only after CLI transient failures are retried up to 3x.

```python
import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.redis import RedisManagementClient

client = RedisManagementClient(DefaultAzureCredential(), os.environ.get('AZURE_SUBSCRIPTION_ID'))
# client bootstrap: see ../../../azure-skill-generator/references/azure-sdk-usage.md#common-client-bootstrap

redis = client.redis.get(
    resource_group_name="{{user.resource_group}}",
    name="{{user.redis_name}}",
)
print(redis.id)
```

Create/update pattern:

```python
poller = client.redis.begin_create_or_update(
    resource_group_name="{{user.resource_group}}",
    name="{{user.redis_name}}",
    parameters={
        "location": "{{user.location}}",
        "sku": {"name": "{{user.sku}}", "family": "{{user.sku_family}}", "capacity": "{{user.capacity}}"},
        "enable_non_ssl_port": False,
    },
)
result = poller.result(timeout=1800)
print(result.id)
```

Delete pattern:

```python
poller = client.redis.begin_delete(
    resource_group_name="{{user.resource_group}}",
    name="{{user.redis_name}}",
)
poller.result(timeout=1800)
```

## Polling

| Operation | Poll Interval | Max Wait |
|-----------|---------------|----------|
| create/update/scale/delete | 30s | 30m |
| reboot | 30s | 15m |
| key regeneration | 15s | 10m |

On timeout, do not repeat mutation. Re-read resource state and report uncertainty.
