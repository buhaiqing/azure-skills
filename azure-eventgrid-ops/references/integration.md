# Azure Event Grid Integration and Commands

## Required Tools

```bash
az version --output json
az account show --output json
az provider show --namespace Microsoft.EventGrid --output json
```

If `Microsoft.EventGrid` is not registered, HALT and ask for approval before registration:

```bash
az provider register --namespace Microsoft.EventGrid --output json
```

## Required RBAC

| Operation | Minimum Role |
|-----------|--------------|
| Read/show/list/metrics | Reader + Monitoring Reader |
| Create/update/delete topic / system topic / domain / domain topic | Contributor on the resource group |
| Create/update/delete event subscription | Contributor on the source resource scope (topic / source resource / domain) |
| Regenerate key on topic / domain | Contributor |
| Send events to topic | `EventGrid Data Sender` (built-in role) on the topic |
| Approve private endpoint connection | Network Contributor on network scope + resource permissions |
| Role assignment changes | User Access Administrator or Owner; prefer delegate to `azure-audit-ops` |

Do not ask for secrets. Use environment credentials through Azure CLI or `DefaultAzureCredential`.

## Pre-flight Checklist

```bash
az account show --output json
az group show --name "{{user.resource_group}}" --output json
az account list-locations --query "[?name=='{{user.location}}']" --output json
az provider show --namespace Microsoft.EventGrid --query "registrationState" --output json
```

For existing topics:

```bash
az eventgrid topic show \
  --name "{{user.topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

For existing event subscriptions on a topic:

```bash
az eventgrid event-subscription list \
  --source-resource-id "{{output.topic_id}}" \
  --output json
```

For metric names:

```bash
az monitor metrics list-definitions \
  --resource "{{output.topic_id}}" \
  --output json
```

For available event types on a topic (used to verify `includedEventTypes`):

```bash
az eventgrid topic list-event-types \
  --resource-group "{{user.resource_group}}" \
  --name "{{user.topic_name}}" \
  --output json
```

## Azure CLI Primary Path

### Topic Operations

```bash
# List topics in resource group
az eventgrid topic list \
  --resource-group "{{user.resource_group}}" \
  --output json

# Show topic
az eventgrid topic show \
  --name "{{user.topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Create topic
az eventgrid topic create \
  --name "{{user.topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --output json

# Update topic (tags, input schema, public network access setting — broaden per Safety Gates)
az eventgrid topic update \
  --name "{{user.topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# List topic keys
az eventgrid topic key list \
  --name "{{user.topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Regenerate key (requires confirmation)
az eventgrid topic key regenerate \
  --name "{{user.topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --key-name key1 \
  --output json

# Delete topic (requires confirmation)
az eventgrid topic show \
  --name "{{user.topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
# After explicit confirmation:
az eventgrid topic delete \
  --name "{{user.topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### System Topic Operations

```bash
# List system topics in resource group
az eventgrid system-topic list \
  --resource-group "{{user.resource_group}}" \
  --output json

# Show system topic
az eventgrid system-topic show \
  --name "{{user.system_topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Create system topic (binds to a source resource)
# --topic-type canonical value: lowercase namespace + resource type, e.g. microsoft.storage.storageaccounts
az eventgrid system-topic create \
  --name "{{user.system_topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --topic-type "microsoft.storage.storageaccounts" \
  --source "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Storage/storageAccounts/{{user.storage_account_name}}" \
  --output json

# Delete system topic (requires confirmation)
az eventgrid system-topic show \
  --name "{{user.system_topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
# After explicit confirmation:
az eventgrid system-topic delete \
  --name "{{user.system_topic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### Domain Operations

```bash
# Create domain
az eventgrid domain create \
  --name "{{user.domain_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --output json

# List domains
az eventgrid domain list \
  --resource-group "{{user.resource_group}}" \
  --output json

# Show domain
az eventgrid domain show \
  --name "{{user.domain_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# List domain keys
az eventgrid domain key list \
  --name "{{user.domain_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Regenerate domain key (requires confirmation)
az eventgrid domain key regenerate \
  --name "{{user.domain_name}}" \
  --resource-group "{{user.resource_group}}" \
  --key-name key1 \
  --output json

# Delete domain (requires confirmation)
az eventgrid domain delete \
  --name "{{user.domain_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### Domain Topic Operations

```bash
# List domain topics
az eventgrid domain topic list \
  --domain-name "{{user.domain_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Show domain topic
az eventgrid domain topic show \
  --domain-name "{{user.domain_name}}" \
  --resource-group "{{user.resource_group}}" \
  --name "{{user.domain_topic_name}}" \
  --output json

# Create domain topic
az eventgrid domain topic create \
  --domain-name "{{user.domain_name}}" \
  --resource-group "{{user.resource_group}}" \
  --name "{{user.domain_topic_name}}" \
  --output json

# Delete domain topic (requires confirmation)
az eventgrid domain topic delete \
  --domain-name "{{user.domain_name}}" \
  --resource-group "{{user.resource_group}}" \
  --name "{{user.domain_topic_name}}" \
  --output json
```

### Event Subscription Operations

The `--source-resource-id` is the full resource ID of the topic / system topic / domain / domain topic / source resource (for system topics).

```bash
# List event subscriptions on a topic
az eventgrid event-subscription list \
  --source-resource-id "{{output.topic_id}}" \
  --output json

# Show event subscription
az eventgrid event-subscription show \
  --name "{{user.event_subscription_name}}" \
  --source-resource-id "{{output.topic_id}}" \
  --output json

# Create event subscription with webhook endpoint and filters
az eventgrid event-subscription create \
  --name "{{user.event_subscription_name}}" \
  --source-resource-id "{{output.topic_id}}" \
  --endpoint "{{user.endpoint_url}}" \
  --subject-begins-with "{{user.subject_begins_with}}" \
  --included-event-types "{{user.included_event_types}}" \
  --max-delivery-attempts {{user.max_delivery_attempts}} \
  --event-ttl {{user.event_ttl_minutes}} \
  --output json

# Create event subscription with Storage Blob dead-letter destination
az eventgrid event-subscription create \
  --name "{{user.event_subscription_name}}" \
  --source-resource-id "{{output.topic_id}}" \
  --endpoint "{{user.endpoint_url}}" \
  --deadletter-endpoint "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Storage/storageAccounts/{{user.storage_account_name}}/blobServices/default/containers/{{user.dead_letter_container}}" \
  --output json

# Create event subscription with CloudEvents schema
# Accepted --event-delivery-schema values: cloudeventschemav1_0, custominputschema, eventgridschema
az eventgrid event-subscription create \
  --name "{{user.event_subscription_name}}" \
  --source-resource-id "{{output.topic_id}}" \
  --endpoint "{{user.endpoint_url}}" \
  --event-delivery-schema cloudeventschemav1_0 \
  --output json

# Update event subscription (filters, retry policy, dead-letter)
az eventgrid event-subscription update \
  --name "{{user.event_subscription_name}}" \
  --source-resource-id "{{output.topic_id}}" \
  --subject-begins-with "{{user.subject_begins_with}}" \
  --max-delivery-attempts {{user.max_delivery_attempts}} \
  --output json

# Delete event subscription (requires confirmation)
az eventgrid event-subscription show \
  --name "{{user.event_subscription_name}}" \
  --source-resource-id "{{output.topic_id}}" \
  --output json
# After explicit confirmation:
az eventgrid event-subscription delete \
  --name "{{user.event_subscription_name}}" \
  --source-resource-id "{{output.topic_id}}" \
  --output json
```

## Publish Events (SDK only — data plane)

Event Grid data plane publishing is not exposed via Azure CLI. Use SDK or REST:

```python
import os
import requests
from azure.core.credentials import AzureSasCredential

# Topic endpoint and SAS key obtained from `az eventgrid topic key list`
endpoint = os.environ["EVENTGRID_TOPIC_ENDPOINT"]
sas_key = os.environ["EVENTGRID_TOPIC_KEY"]

# SAS-based publish (use only with topic access keys; not for system topics)
requests.post(
    f"{endpoint}?api-version=2020-06-01",
    headers={"aeg-sas-key": sas_key},
    json=[{
        "id": "1",
        "subject": "test/event",
        "eventType": "Contoso.Items.Created",
        "eventTime": "2026-07-11T00:00:00Z",
        "data": {"itemId": "abc-123"},
        "dataVersion": "1.0",
    }],
    timeout=10,
)
```

For system topics, event publishing is owned by the Azure source resource — you only create event subscriptions, never publish.

## Azure SDK Fallback

Use SDK only after CLI transient failures are retried up to 3x.

SDK package: `azure-mgmt-eventgrid` (version 10.4.0 verified 2026-07-11 via `pip install azure-mgmt-eventgrid`).

Verified SDK operations via introspection (`EventGridManagementClient`):

| Operations Class | Verified Methods |
|---|---|
| `client.topics` | `begin_create_or_update`, `begin_delete`, `begin_regenerate_key`, `begin_update`, `get`, `list_by_resource_group`, `list_by_subscription`, `list_event_types`, `list_shared_access_keys` |
| `client.system_topics` | `begin_create_or_update`, `begin_delete`, `begin_update`, `get`, `list_by_resource_group`, `list_by_subscription` |
| `client.domains` | `begin_create_or_update`, `begin_delete`, `begin_update`, `get`, `list_by_resource_group`, `list_by_subscription`, `list_shared_access_keys`, `regenerate_key` (non-LRO) |
| `client.domain_topics` | `begin_create_or_update`, `begin_delete`, `get`, `list_by_domain` |
| `client.event_subscriptions` | `begin_create_or_update`, `begin_delete`, `begin_update`, `get`, `get_delivery_attributes`, `get_full_url`, `list_by_domain_topic`, `list_by_resource`, `list_global_by_resource_group`, `list_global_by_subscription`, `list_regional_by_resource_group`, `list_regional_by_subscription`, plus `*_for_topic_type` variants |
| `client.private_endpoint_connections` | `begin_delete`, `begin_update`, `get`, `list_by_resource` |

```python
import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.eventgrid import EventGridManagementClient

credential = DefaultAzureCredential()
client = EventGridManagementClient(
    credential,
    subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
)

# Create topic (LRO)
poller = client.topics.begin_create_or_update(
    resource_group_name="{{user.resource_group}}",
    topic_name="{{user.topic_name}}",
    topic_info={
        "location": "{{user.location}}",
    },
)
topic = poller.result(timeout=1800)
print(topic.id)

# Create event subscription on topic (LRO)
# `scope` is the full resource ID of the topic
poller = client.event_subscriptions.begin_create_or_update(
    scope="{{output.topic_id}}",
    event_subscription_name="{{user.event_subscription_name}}",
    event_subscription_info={
        "destination": {
            "endpoint_type": "WebHook",
            "properties": {
                "endpoint_url": "{{user.endpoint_url}}",
                # Or use Azure Event Hub / Service Bus / Storage Queue destination
            },
        },
        "filter": {
            "subject_begins_with": "{{user.subject_begins_with}}",
            "included_event_types": [
                t.strip() for t in "{{user.included_event_types}}".split(",") if t.strip()
            ],  # Empty list means all event types
        },
        "retry_policy": {
            "max_delivery_attempts": {{user.max_delivery_attempts}},
            "event_time_to_live_in_minutes": {{user.event_ttl_minutes}},
        },
    },
)
event_subscription = poller.result(timeout=1800)
print(event_subscription.id)

# Get delivery attributes for an existing subscription (sync)
# Returns DeliveryAttributeMapping (HTTP header attribute mappings), NOT delivery counters.
attributes = client.event_subscriptions.get_delivery_attributes(
    scope="{{output.topic_id}}",
    event_subscription_name="{{user.event_subscription_name}}",
)
# attributes.value is a list of DeliveryAttributeMapping entries ({name, value})
for attr in attributes.value or []:
    print(f"{attr.name}: {attr.value}")

# List topic keys (sync)
keys = client.topics.list_shared_access_keys(
    resource_group_name="{{user.resource_group}}",
    topic_name="{{user.topic_name}}",
)
print(keys.key1)

# Regenerate topic key (LRO — topics)
poller = client.topics.begin_regenerate_key(
    resource_group_name="{{user.resource_group}}",
    topic_name="{{user.topic_name}}",
    regenerate_key_request={"key_name": "key1"},
)
new_keys = poller.result(timeout=1800)
print(new_keys.key1)

# Delete topic (LRO) — requires confirmation
poller = client.topics.begin_delete(
    resource_group_name="{{user.resource_group}}",
    topic_name="{{user.topic_name}}",
)
poller.result(timeout=1800)
```

## Polling

| Operation | Poll Interval | Max Wait |
|-----------|---------------|----------|
| topic create / update / delete (LRO) | 30s | 30m |
| system topic create / update / delete (LRO) | 30s | 30m |
| domain create / update / delete (LRO) | 30s | 30m |
| domain topic create / delete (LRO) | 30s | 30m |
| event subscription create / update / delete (LRO) | 30s | 30m |
| topic key regenerate (LRO) | 30s | 30m |
| list keys / show / list (sync) | N/A | N/A |
| get_delivery_attributes (sync) | N/A | N/A |

On timeout, do not repeat mutation. Re-read resource state and report uncertainty.