# Azure Event Hubs Core Concepts

## Service Tiers

| Tier | Use Case | Key Limits |
|------|----------|------------|
| Basic | Low-throughput event ingestion | 1 consumer group per event hub, no Capture, no auto-inflate |
| Standard | General event streaming | Up to 20 TUs, auto-inflate, Capture, Kafka support, 1 MB/s ingress per TU |
| Premium | Predictable performance, larger scale | Processing Units (PUs), fixed pricing, >20 TUs equivalent |
| Dedicated | High-throughput, isolated capacity | Clusters, full isolation, no TU limits |

Always identify the exact resource type before operating. `az eventhubs namespace` is the CLI surface; Premium uses PUs (processing units) not TUs (throughput units).

## Resource Identity

Use full resource IDs in reports and traces:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.EventHub/namespaces/{{user.namespace_name}}
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.EventHub/namespaces/{{user.namespace_name}}/eventhubs/{{user.eventhub_name}}
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.EventHub/namespaces/{{user.namespace_name}}/eventhubs/{{user.eventhub_name}}/consumergroups/{{user.consumer_group_name}}
```

## Key Concepts

| Concept | Meaning | Operational Impact |
|---------|---------|--------------------|
| Namespace | Container for event hubs, Kafka endpoint | All operations scoped to namespace |
| Event Hub | Event stream (topic-like) inside namespace | Partition count fixed at creation; cannot be changed |
| Partition | Ordered event buffer within an event hub | Partition key decides routing; partition skew causes throttling |
| Consumer Group | View of event stream per consumer app | $Default exists; create custom for multiple consumers |
| Throughput Unit (TU) | Standard tier capacity unit (1 MB/s ingress, 2 MB/s egress) | Throttled when exceeded; auto-inflate mitigates |
| Processing Unit (PU) | Premium tier capacity unit | Higher per-unit throughput than TU |
| Capture | Automatic event archiving to Blob Storage | Requires storage account; configurable at event hub level |
| Auto-inflate | Automatic TU scaling based on load | Min/max TU range configurable |
| Kafka endpoint | Namespace provides a Kafka-compatible endpoint | Enable at namespace creation; cannot be toggled after creation |

## Metrics Used for Operations

| Metric | Signal |
|--------|--------|
| `IncomingMessages` / `OutgoingMessages` | Message throughput |
| `IncomingBytes` / `OutgoingBytes` | Bandwidth usage |
| `ThrottledRequests` | TU/PU capacity pressure |
| `IncomingRequestBytes` | Per-second ingress bytes |
| `SuccessfulRequests` | Healthy request ratio |
| `ServerErrors` / `UserErrors` | Error rate breakdown |
| `ActiveConnections` | Connection count |
| `CaptureBacklog` | Capture falling behind (bytes) |
| `ConsumerLag` | Consumer processing lag per partition |

Verify exact metric names with `az monitor metrics list-definitions` for the target resource. Do not invent names in final reports.

## Common Architecture Patterns

### Standard Namespace with Auto-inflate

Recommended for variable workloads. Set min/max TU range (e.g. 1-10). Auto-inflate scales up on throttling but does not scale down.

### Kafka-compatible Endpoint

Enable Kafka at namespace creation time. Applications use standard Kafka client libraries with the Event Hubs connection string. Use SASL/SSL authentication.

### Capture to Blob Storage

Configures automatic archiving of events to Azure Blob Storage in Avro format. Requires a storage account with a container. Toggle on/off per event hub.

### Private Endpoint

Preferred for production. Check:
- private endpoint connection state;
- Private DNS zone record;
- VNet link;
- client subnet DNS resolver behavior.

## Delegation Boundaries

| Need | Delegate |
|------|----------|
| Cost analysis | `azure-cost-ops` |
| Generic Azure Monitor KQL/alert management | `azure-monitor-ops` |
| RBAC, Activity Log, locks, policy-only work | `azure-audit-ops` |
| Deep Capture storage detail | `azure-blobstorage-ops` |
| Azure Function trigger setup | `azure-function-ops` |
| Deep VNet/Private DNS design | network owner after this skill provides entry diagnostics |
| Application code consumer strategy | app owner; this skill reports evidence and recommendations |
