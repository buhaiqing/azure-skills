# Azure Event Grid Core Concepts

## Resource Hierarchy

Event Grid has four resource types. Always identify the exact type before operating.

| Resource | Purpose | Notes |
|----------|---------|-------|
| **Topic** | Custom endpoint for application-published events | User publishes via SDK / REST with topic access key |
| **System Topic** | Built-in topic representing an Azure source resource (Storage Account, Event Hubs namespace, etc.) | Created automatically when Azure resource emits events; also creatable via `az eventgrid system-topic create` |
| **Domain** | Container for many topics (multi-tenant scenarios) | Up to 100,000 topics per domain; single access key for all topics |
| **Domain Topic** | Topic within a domain | Identified by `/domains/{domain}/topics/{topic}` |

## Resource Identity

Use full resource IDs in reports and traces:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.EventGrid/topics/{{user.topic_name}}
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.EventGrid/systemTopics/{{user.system_topic_name}}
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.EventGrid/domains/{{user.domain_name}}
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.EventGrid/domains/{{user.domain_name}}/topics/{{user.domain_topic_name}}
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.EventGrid/topics/{{user.topic_name}}/providers/Microsoft.EventGrid/eventSubscriptions/{{user.event_subscription_name}}
```

System Topic event subscriptions live under the source resource (not under the system topic), so the resource ID contains the system topic's *source* resource.

## Event Subscriptions

Event subscriptions are children of a topic (custom or system) or domain topic. They declare where events are delivered and which events to filter.

| Property | Purpose | Operational Impact |
|----------|---------|--------------------|
| `destination` | Where events are sent | Webhook (HTTP), Event Hub, Service Bus queue/topic, Storage Queue, hybrid connection |
| `filter.subjectBeginsWith` | Match events whose `subject` field starts with the prefix | Reduces event volume; multiple subscriptions on one topic can fan out |
| `filter.subjectEndsWith` | Match events whose `subject` field ends with the suffix | Combine with `subjectBeginsWith` for tighter filtering |
| `filter.includedEventTypes` | Whitelist of event types | Empty = all event types delivered |
| `filter.advancedFilters` | JSON-path / value comparisons (`StringContains`, `NumberGreaterThan`, `BoolEquals`, etc.) | Up to 25 advanced filters per subscription; combine with `operatorType: And` / `Or` |
| `deadLetterWithResourceIdentity` | Dead-letter destination on terminal failure | Storage Blob container with SAS; system-assigned or user-assigned managed identity |
| `retryPolicy.maxDeliveryAttempts` | Retry count before dead-lettering | Range 1-30; default 30 |
| `retryPolicy.eventTimeToLiveInMinutes` | Event TTL before dropping | Range 1-1440; default 1440 (24h) |
| `eventDeliverySchema` | `EventGridSchema` (default) or `CloudEventSchemaV1_0` | Choose once at create; CloudEvents adds `ce-` envelope fields |
| `deliveryWithResourceIdentity` | Use managed identity for delivery to AAD-protected handlers | Required when handler enforces AAD auth |

## Event Schemas

| Schema | Envelope | When to use |
|--------|----------|-------------|
| **Event Grid Schema** (`EventGridSchema`) | Top-level array with `id`, `subject`, `eventType`, `eventTime`, `data`, `dataVersion` | Default; Azure-internal events |
| **CloudEvents v1.0** (`CloudEventSchemaV1_0`) | CloudEvents JSON envelope with `id`, `source`, `type`, `time`, `data`, `specversion: "1.0"` | CNCF standard; cross-cloud portability |

Always match schema to handler expectation. Mixing schemas causes handler-side parsing errors.

## Event Delivery Lifecycle

```
Publisher
  │
  ▼
Topic / System Topic / Domain
  │
  ▼
Subscription filter (subjectBeginsWith, eventType, advancedFilters)
  │  (filtered-out events are dropped silently)
  ▼
Retry policy: maxDeliveryAttempts × exponential backoff
  │  (1 attempt = initial; further attempts = retries on failure)
  ▼
Destination (webhook / Event Hub / Service Bus / Storage Queue / hybrid connection)
  │  ◀── handler returns 200 OK = success
  │  ◀── handler returns 5xx / timeout / 4xx (except 4xx other than 408/429) = retryable
  │  ◀── retries exhausted = dead-letter destination
  ▼
Dead-letter (Storage Blob container with SAS)
```

## Common Architecture Patterns

### Custom Topic for Application Events

Application code publishes events to the topic endpoint using a topic access key. Subscribers receive via webhook or push to a queue. Topic access keys are rotated via `key regenerate`.

### System Topic for Azure Resource Events

Azure services (Storage Account, Event Hubs, Resource Group, Subscription) emit events to a system topic automatically. You only create event subscriptions on the system topic — no publishing. Delete the source resource only after deleting the system topic (system topic lifecycle depends on source).

### Event Domain for Multi-Tenant Routing

Domains group thousands of topics under one namespace. Tenants each get a `domain topic`. A single access key authenticates publishers; per-tenant event subscriptions filter to specific tenants.

### Dead-Letter Inspection

Standard operational pattern: route dead-lettered events to a Storage Blob container with SAS, then run scheduled job to inspect, alert on age > N hours, and replay manually if safe.

## Quotas and Limits

| Resource | Default Limit |
|----------|---------------|
| Custom topics per subscription | 100 |
| Event subscriptions per topic | 500 |
| Event subscriptions per domain | 100,000 |
| Advanced filters per subscription | 25 |
| Event size (Event Grid Schema) | 1 MB |
| Event size (CloudEvents) | 1 MB |
| Publish rate (ingress) | 5,000 events/sec per topic (ingress varies by region) |
| Topics per domain | 100,000 |

Check current quota with `az eventgrid topic list --query "length([])"` for inventory, and check Azure portal / `az quota list` for limits.

## Delegation Boundaries

| Need | Delegate |
|------|----------|
| Cost analysis | `azure-cost-ops` |
| Generic Azure Monitor KQL/alert management | `azure-monitor-ops` |
| RBAC, Activity Log, locks, policy-only work | `azure-audit-ops` |
| Webhook handler in Azure Function | `azure-function-ops` |
| Service Bus destination configuration | `azure-servicebus-ops` |
| Event Hubs destination configuration | `azure-eventhub-ops` |
| Storage Queue destination / Dead-letter storage account | `azure-queue-storage-ops` / `azure-blobstorage-ops` |
| Private DNS / VNet deep design | network owner after this skill provides entry diagnostics |
| Schema validation in handler code | app owner; this skill reports evidence and recommendations |