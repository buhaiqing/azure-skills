# Azure Service Bus Integration and Commands

SDK 方法名经实测校验（`azure-mgmt-servicebus==9.0.0`，`ServiceBusManagementClient`）。

## Required Tools

```bash
az version --output json
az account show --output json
az provider show --namespace Microsoft.ServiceBus --output json
```

If `Microsoft.ServiceBus` is not registered, HALT and ask for approval before registration:

```bash
az provider register --namespace Microsoft.ServiceBus --output json
```

## Required RBAC

| Operation | Minimum Role |
|-----------|--------------|
| Read/show/list | Reader + Monitoring Reader |
| Create/update/delete | Contributor or Azure Service Bus Data Owner |
| Authorization rule/keys | Azure Service Bus Data Owner |
| Private endpoint connection approval | Network Contributor on network scope + resource permissions |
| Role assignment changes | User Access Administrator or Owner; prefer delegate to `azure-audit-ops` |

Do not ask for secrets. Use environment credentials through Azure CLI or `DefaultAzureCredential`.

## Pre-flight Checklist

```bash
az account show --output json
az group show --name "{{user.resource_group}}" --output json
az account list-locations --query "[?name=='{{user.location}}']" --output json
az provider show --namespace Microsoft.ServiceBus --query "registrationState" --output json
```

For existing resources:

```bash
az servicebus namespace show \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

## Azure CLI Primary Path

### List and Show

```bash
az servicebus namespace list \
  --resource-group "{{user.resource_group}}" \
  --output json

az servicebus namespace show \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az servicebus queue list \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az servicebus queue show \
  --name "{{user.queue_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az servicebus topic list \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az servicebus topic show \
  --name "{{user.topic_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az servicebus topic subscription list \
  --topic-name "{{user.topic_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az servicebus topic subscription show \
  --name "{{user.subscription_name}}" \
  --topic-name "{{user.topic_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### Create Namespace

```bash
az servicebus namespace create \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --sku Standard \
  --output json
```

Validate:

```bash
az servicebus namespace show \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id, state:provisioningState, sku:sku.name}" \
  --output json
```

### Create Queue

```bash
az servicebus queue create \
  --name "{{user.queue_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --default-message-time-to-live "P14D" \
  --max-delivery-count 10 \
  --enable-dead-lettering-on-message-expiration true \
  --output json
```

### Create Topic

```bash
az servicebus topic create \
  --name "{{user.topic_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --default-message-time-to-live "P14D" \
  --enable-duplicate-detection true \
  --duplicate-detection-history-time-window "PT30S" \
  --output json
```

### Create Subscription

```bash
az servicebus topic subscription create \
  --name "{{user.subscription_name}}" \
  --topic-name "{{user.topic_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --enable-dead-lettering-on-message-expiration true \
  --max-delivery-count 10 \
  --output json
```

### Create Rule (Filter)

```bash
az servicebus topic subscription rule create \
  --name "{{user.rule_name}}" \
  --subscription-name "{{user.subscription_name}}" \
  --topic-name "{{user.topic_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --filter-sql-expression "1=1" \
  --output json
```

### Authorization Rules

```bash
# Namespace authorization rules
az servicebus namespace authorization-rule list \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az servicebus namespace authorization-rule keys list \
  --name "RootManageSharedAccessKey" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Queue authorization rules
az servicebus queue authorization-rule keys list \
  --name "{{user.auth_rule_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --queue-name "{{user.queue_name}}" \
  --output json

# Topic authorization rules
az servicebus topic authorization-rule keys list \
  --name "{{user.auth_rule_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --topic-name "{{user.topic_name}}" \
  --output json
```

### Regenerate Keys

```bash
az servicebus namespace authorization-rule keys renew \
  --name "RootManageSharedAccessKey" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --key PrimaryKey \
  --output json
```

Requires confirmation and client rotation plan. Prefer secondary-key rotation first.

### Delete

```bash
az servicebus namespace show \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# After explicit confirmation:
az servicebus namespace delete \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

Queue/topic/subscription/rule deletion follows the same pattern with the respective show + delete commands.

## Azure SDK Fallback

Use SDK only after CLI transient failures are retried up to 3x.

```python
# 注：{{user.*}} 占位符为伪代码模板，Agent 执行时替换为实际值。
import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.servicebus import ServiceBusManagementClient

credential = DefaultAzureCredential()
client = ServiceBusManagementClient(
    credential,
    subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
)

# Get namespace
namespace = client.namespaces.get(
    resource_group_name="{{user.resource_group}}",
    namespace_name="{{user.namespace_name}}",
)
print(namespace.id)
```

Create/update pattern (queues):

```python
poller = client.queues.begin_create_or_update(
    resource_group_name="{{user.resource_group}}",
    namespace_name="{{user.namespace_name}}",
    queue_name="{{user.queue_name}}",
    parameters={
        "location": "{{user.location}}",
        "properties": {
            "defaultMessageTimeToLive": "P14D",
            "maxDeliveryCount": 10,
            "deadLetteringOnMessageExpiration": True,
        },
    },
)
result = poller.result(timeout=1800)
print(result.id)
```

Topics:

```python
poller = client.topics.begin_create_or_update(
    resource_group_name="{{user.resource_group}}",
    namespace_name="{{user.namespace_name}}",
    topic_name="{{user.topic_name}}",
    parameters={
        "location": "{{user.location}}",
        "properties": {
            "defaultMessageTimeToLive": "P14D",
            "requiresDuplicateDetection": True,
            "duplicateDetectionHistoryTimeWindow": "PT30S",
        },
    },
)
result = poller.result(timeout=1800)
```

Subscriptions:

```python
poller = client.subscriptions.begin_create_or_update(
    resource_group_name="{{user.resource_group}}",
    namespace_name="{{user.namespace_name}}",
    topic_name="{{user.topic_name}}",
    subscription_name="{{user.subscription_name}}",
    parameters={
        "properties": {
            "deadLetteringOnMessageExpiration": True,
            "maxDeliveryCount": 10,
        },
    },
)
result = poller.result(timeout=1800)
```

Delete pattern:

```python
poller = client.namespaces.begin_delete(
    resource_group_name="{{user.resource_group}}",
    namespace_name="{{user.namespace_name}}",
)
poller.result(timeout=1800)
```

## Verified SDK Method Inventory (azure-mgmt-servicebus==9.0.0)

| Operations Class | Methods |
|------------------|---------|
| `client.namespaces` | `begin_create_or_update`, `begin_delete`, `check_name_availability`, `create_or_update_authorization_rule`, `create_or_update_network_rule_set`, `delete_authorization_rule`, `get`, `get_authorization_rule`, `get_network_rule_set`, `list`, `list_authorization_rules`, `list_by_resource_group`, `list_keys`, `list_network_rule_sets`, `regenerate_keys`, `update` |
| `client.queues` | `create_or_update`, `create_or_update_authorization_rule`, `delete`, `delete_authorization_rule`, `get`, `get_authorization_rule`, `list_authorization_rules`, `list_by_namespace`, `list_keys`, `regenerate_keys` |
| `client.topics` | `create_or_update`, `create_or_update_authorization_rule`, `delete`, `delete_authorization_rule`, `get`, `get_authorization_rule`, `list_authorization_rules`, `list_by_namespace`, `list_keys`, `regenerate_keys` |
| `client.subscriptions` | `create_or_update`, `delete`, `get`, `list_by_topic` |
| `client.rules` | `create_or_update`, `delete`, `get`, `list_by_subscriptions` |
| `client.disaster_recovery_configs` | `break_pairing`, `check_name_availability`, `create_or_update`, `delete`, `fail_over`, `get`, `get_authorization_rule`, `list`, `list_authorization_rules`, `list_keys` |
| `client.migration_configs` | `begin_create_and_start_migration`, `complete_migration`, `delete`, `get`, `list`, `revert` |
| `client.private_endpoint_connections` | `begin_delete`, `create_or_update`, `get`, `list` |
| `client.private_link_resources` | `get` |
| `client.operations` | `list` |

**Note**: `queues` uses `create_or_update` (no `begin_` prefix — non-LRO). `namespaces` uses `begin_create_or_update` / `begin_delete` (LRO). Do NOT use `begin_create_or_update` on queues, topics, or subscriptions.

## Polling

| Operation | Poll Interval | Max Wait |
|-----------|---------------|----------|
| namespace create/delete | 30s | 30m |
| queue/topic/subscription create/delete | 15s | 10m |
| authorization rule create/delete | 15s | 5m |

On timeout, do not repeat mutation. Re-read resource state and report uncertainty.
