# Azure Service Bus Core Concepts

## Service Architecture

Azure Service Bus is a fully managed enterprise message broker with two messaging patterns:

| Pattern | Resource | Use Case |
|---------|----------|----------|
| Point-to-point | Queue | Each message consumed by one receiver; competing consumer pattern |
| Publish-subscribe | Topic + Subscriptions | Each message fanned out to multiple subscriptions; each subscription has its own consumer group |

## Namespace

A namespace is the scoping container for all Service Bus resources. It provides:

- **DNS name**: `{namespace}.servicebus.windows.net`
- **Connection string**: Derived from authorization rules
- **SKU tiers**: Basic, Standard, Premium
- **Capacity units**: Premium tier supports Messaging Units (1, 2, 4, 8, 16)

## Resource Hierarchy

```
Namespace
├── Queue                      (point-to-point)
├── Topic                      (pub-sub root)
│   └── Subscription           (topic consumer group)
│       └── Rule (Filter)      (SQL filter / correlation filter)
└── Authorization Rule         (shared access policy on namespace/queue/topic)
```

## Key Concepts

| Concept | Meaning | Operational Impact |
|---------|---------|--------------------|
| Message Time-to-Live (TTL) | Max message lifetime before auto-expiry | Too short → messages expire before processing; too long → stale messages accumulate |
| Max Delivery Count | Max retries before message is dead-lettered | Too low → legitimate messages dead-lettered; too high → poison messages loop |
| Dead-Letter Queue (DLQ) | Sub-queue for undeliverable messages | DLQ growth signals processing failures; needs investigation |
| Duplicate Detection | Deduplicates messages within a time window | Prevents duplicates but adds overhead; window up to 7 days |
| Partitioning | Distributes load across multiple message brokers | Required for high throughput in Basic/Standard; enabled at creation |
| Sessions | First-in-first-out ordering within a session | Enables message ordering; requires session-aware consumers |
| Auto-forwarding | Automatically forward messages to another queue/topic | Chaining or load balancing; can create forwarding loops |
| Message Lock | Lock duration for peek-lock receive mode | Too short → message re-processed before completion; too long → blocked consumers |

## SKU Comparison

| Feature | Basic | Standard | Premium |
|---------|-------|----------|---------|
| Queues/Topics | 100 | 5,000 | Unlimited per capacity |
| Message size | 256 KB | 256 KB | 1 MB |
| Duplicate detection | No | Yes | Yes |
| Sessions | No | Yes | Yes |
| Dead-letter | No | Yes | Yes |
| Auto-forwarding | No | Yes | Yes |
| VNet integration | No | No | Yes |
| Private endpoint | No | No | Yes |
| Geo-disaster recovery | No | No | Yes |

## Dead-Letter Queue (DLQ) Triggers

Messages are moved to the DLQ when:
- **Expired**: Message TTL exceeded and `deadLetteringOnMessageExpiration` is enabled
- **Delivery count exceeded**: MaxDeliveryCount reached (poison message)
- **Filter mismatch** (topics only): No rule matches the message (with `deadLetteringOnFilterEvaluationExceptions` enabled)
- **Session violation**: Session ID mismatch or session lock lost

## Metrics Used for Operations

| Metric | Signal |
|--------|--------|
| `IncomingMessages` | Inbound throughput |
| `OutgoingMessages` | Outbound throughput |
| `ActiveMessages` | Current backlog depth |
| `DeadletteredMessages` | Undeliverable message count |
| `SuccessfulRequests` | Healthy request rate |
| `ThrottledRequests` | Quota/rate-limiting pressure |
| `ServerErrors` | Service-side failures |
| `UserErrors` | Client-side errors |
| `NamespaceCpuUsage` | Premium namespace CPU |
| `NamespaceMemoryUsage` | Premium namespace memory |

Verify exact metric names with `az monitor metrics list-definitions` for the target resource.

## Delegation Boundaries

| Need | Delegate |
|------|----------|
| Cost analysis | `azure-cost-ops` |
| Generic Azure Monitor KQL/alert management | `azure-monitor-ops` |
| RBAC, Activity Log, locks, policy-only work | `azure-audit-ops` |
| Logic Apps / Event Grid message routing | Respective skill (TBD) |
| Application code consumer pattern redesign | App owner; this skill reports evidence and recommendations |
