# Azure Event Hubs Integration and Commands

## Required Tools

```bash
az version --output json
az account show --output json
az provider show --namespace Microsoft.EventHub --output json
```

If `Microsoft.EventHub` is not registered, HALT and ask for approval before registration:

```bash
az provider register --namespace Microsoft.EventHub --output json
```

## Required RBAC

| Operation | Minimum Role |
|-----------|--------------|
| Read/show/list/metrics | Reader + Monitoring Reader |
| Create/update/delete namespace/event hub/consumer group | Contributor or Azure Event Hubs Data Owner |
| Authorization rule management | Contributor |
| Regenerate keys | Contributor or Azure Event Hubs Data Owner |
| Private endpoint connection approval | Network Contributor on network scope + resource permissions |
| Role assignment changes | User Access Administrator or Owner; prefer delegate to `azure-audit-ops` |

Do not ask for secrets. Use environment credentials through Azure CLI or `DefaultAzureCredential`.

## Pre-flight Checklist

```bash
az account show --output json
az group show --name "{{user.resource_group}}" --output json
az account list-locations --query "[?name=='{{user.location}}']" --output json
az provider show --namespace Microsoft.EventHub --query "registrationState" --output json
```

For existing namespaces:

```bash
az eventhubs namespace show \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

For metric names:

```bash
az monitor metrics list-definitions \
  --resource "{{output.namespace_id}}" \
  --output json
```

## Azure CLI Primary Path

### Namespace Operations

```bash
# List namespaces in resource group
az eventhubs namespace list \
  --resource-group "{{user.resource_group}}" \
  --output json

# Show namespace
az eventhubs namespace show \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Create namespace (--enable-auto-inflate: true/false; use --maximum-throughput-units <int> when enabling)
az eventhubs namespace create \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --sku "{{user.sku}}" \
  --capacity "{{user.throughput_units}}" \
  --enable-auto-inflate false \
  --output json

# Update namespace (SKU, capacity, auto-inflate)
az eventhubs namespace update \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --sku "{{user.sku}}" \
  --capacity "{{user.throughput_units}}" \
  --output json

# Delete namespace (requires confirmation)
az eventhubs namespace show \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
# After explicit confirmation:
az eventhubs namespace delete \
  --name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### Event Hub Operations

```bash
# List event hubs in namespace
az eventhubs eventhub list \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Show event hub
az eventhubs eventhub show \
  --name "{{user.eventhub_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Create event hub
az eventhubs eventhub create \
  --name "{{user.eventhub_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --partition-count {{user.partition_count}} \
  --message-retention 7 \
  --output json

# Update event hub (enable Capture, message retention)
az eventhubs eventhub update \
  --name "{{user.eventhub_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --capture-enabled true \
  --message-retention {{user.message_retention_days}} \
  --output json

# Delete event hub (requires confirmation)
az eventhubs eventhub show \
  --name "{{user.eventhub_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
# After explicit confirmation:
az eventhubs eventhub delete \
  --name "{{user.eventhub_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### Consumer Group Operations

```bash
# List consumer groups for event hub
az eventhubs eventhub consumer-group list \
  --eventhub-name "{{user.eventhub_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Show consumer group
az eventhubs eventhub consumer-group show \
  --name "{{user.consumer_group_name}}" \
  --eventhub-name "{{user.eventhub_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Create consumer group
az eventhubs eventhub consumer-group create \
  --name "{{user.consumer_group_name}}" \
  --eventhub-name "{{user.eventhub_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Delete consumer group (requires confirmation)
az eventhubs eventhub consumer-group delete \
  --name "{{user.consumer_group_name}}" \
  --eventhub-name "{{user.eventhub_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### Authorization Rules and Keys

```bash
# List authorization rules for namespace
az eventhubs namespace authorization-rule list \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# List keys
az eventhubs namespace authorization-rule keys list \
  --name "{{user.rule_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Regenerate key (requires confirmation)
az eventhubs namespace authorization-rule keys renew \
  --name "{{user.rule_name}}" \
  --namespace-name "{{user.namespace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --key-type PrimaryKey \
  --output json
```

## Azure SDK Fallback

Use SDK only after CLI transient failures are retried up to 3x.

SDK package: `azure-mgmt-eventhub` (version 11.2.0 verified 2026-07-11).

Verified SDK operations via introspection (`EventHubManagementClient`):

| Operations Class | Verified Methods |
|---|---|
| `client.namespaces` | `begin_create_or_update`, `begin_delete`, `get`, `update`, `list`, `list_by_resource_group`, `check_name_availability`, `list_keys`, `regenerate_keys` |
| `client.event_hubs` | `create_or_update`, `delete`, `get`, `list_by_namespace`, `list_keys`, `regenerate_keys` |
| `client.consumer_groups` | `create_or_update`, `delete`, `get`, `list_by_event_hub` |

```python
import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.eventhub import EventHubManagementClient

credential = DefaultAzureCredential()
client = EventHubManagementClient(
    credential,
    subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
)

# Get namespace
namespace = client.namespaces.get(
    resource_group_name="{{user.resource_group}}",
    namespace_name="{{user.namespace_name}}",
)
print(namespace.id)

# Create namespace (LRO)
poller = client.namespaces.begin_create_or_update(
    resource_group_name="{{user.resource_group}}",
    namespace_name="{{user.namespace_name}}",
    parameters={
        "location": "{{user.location}}",
        "sku": {"name": "{{user.sku}}", "tier": "{{user.sku}}", "capacity": {{user.throughput_units}}},
    },
)
result = poller.result(timeout=1800)
print(result.id)

# Create event hub
eventhub = client.event_hubs.create_or_update(
    resource_group_name="{{user.resource_group}}",
    namespace_name="{{user.namespace_name}}",
    event_hub_name="{{user.eventhub_name}}",
    parameters={
        "location": "{{user.location}}",
        "partition_count": {{user.partition_count}},
        "message_retention_in_days": 7,
    },
)
print(eventhub.id)

# Delete namespace (LRO) — requires confirmation
poller = client.namespaces.begin_delete(
    resource_group_name="{{user.resource_group}}",
    namespace_name="{{user.namespace_name}}",
)
poller.result(timeout=1800)

# Update namespace (non-LRO, returns Optional[EHNamespace])
namespace = client.namespaces.update(
    resource_group_name="{{user.resource_group}}",
    namespace_name="{{user.namespace_name}}",
    parameters={
        "sku": {"name": "{{user.sku}}", "capacity": {{user.throughput_units}}},
    },
)
print(namespace.id if namespace else "update completed")
```

## Polling

| Operation | Poll Interval | Max Wait |
|-----------|---------------|----------|
| namespace create/update/delete (LRO) | 30s | 30m |
| event hub create/update/delete (non-LRO, synchronous) | N/A | N/A |
| consumer group create/delete (non-LRO, synchronous) | N/A | N/A |

On timeout, do not repeat mutation. Re-read resource state and report uncertainty.
