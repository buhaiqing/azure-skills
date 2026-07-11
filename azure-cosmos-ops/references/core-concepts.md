# Azure Cosmos DB Core Concepts

## Supported Scope

This skill targets Azure Cosmos DB accounts and their API models. The account is the top-level resource; databases and containers live beneath it. API model is fixed at account creation and cannot be changed afterward.

## Resource Identity

Use full resource IDs in reports and traces:

```text
# Account
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.DocumentDB/databaseAccounts/{{user.account_name}}

# SQL container
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.DocumentDB/databaseAccounts/{{user.account_name}}/sqlDatabases/{{user.database_name}}/containers/{{user.container_name}}
```

## API Models

| API | Account `kind` | Notes |
|-----|----------------|-------|
| SQL (Core) | `GlobalDocumentDB` | Native SQL/NoSQL API; this skill documents it in detail |
| MongoDB | `MongoDB` | Wire-compatible with MongoDB; use `az cosmosdb mongodb ...` |
| Cassandra | `GlobalDocumentDB` | Column-family; use `az cosmosdb cassandra ...` |
| Gremlin | `GlobalDocumentDB` | Graph; use `az cosmosdb gremlin ...` |
| Table | `GlobalDocumentDB` | Table storage API; use `az cosmosdb table ...` |

Confirm the API model with `az cosmosdb show` before database/container operations.

## Key Concepts

| Concept | Meaning | Operational Impact |
|---------|---------|--------------------|
| Request Unit (RU) | Normalized throughput currency for every read/write/query | Drives RU/s provisioning and throttling |
| Manual throughput | Fixed RU/s (e.g. 400) | Predictable cost; can throttle if underestimated |
| Autoscale | RU/s scales between 10% and 100% of a max (e.g. 4000) | Absorbs bursts; costs at peak usage |
| Partition key | Defines physical data distribution | Poor choice causes hot partition / storage skew |
| Physical partition | Storage + throughput unit (max ~20 GB, capped RU/s) | Hot key saturates one partition |
| Consistency level | Strong / Bounded Staleness / Session / Consistent Prefix / Eventual | Stronger = higher RU cost and latency |
| Global distribution | Replicated read/write regions | Multi-region writes risk conflict; failover changes write region |
| Normalized RU consumption | % of provisioned RU/s used | Primary signal for throttling root cause |
| TTL | Document/container time-to-live | Controls storage growth |

## Throughput Models

- Account-level (shared) throughput: databases/containers without dedicated RU/s draw from the account.
- Database-level throughput: shared across containers in that database.
- Container-level throughput: dedicated to one container (supports autoscale).
- Minimum RU/s and max storage per physical partition differ by API; verify with docs before provisioning.

## Operational States

| State | Meaning | Action |
|-------|---------|--------|
| Succeeded | Account/container ready | Continue |
| Creating/Updating/Deleting | LRO in progress | Poll; do not start another mutation |
| Failed | Provisioning failed | HALT and inspect error/Activity Log |
| Disabled/Inaccessible | Control-plane or billing/security issue | HALT and investigate |

## Metrics Used for Operations

| Metric | Signal |
|--------|--------|
| `TotalRequestUnits` | Aggregate RU consumed |
| `TotalRequestCharge` where available | Per-op RU cost |
| `NormalizedRUConsumption` | % of provisioned RU/s used (throttling predictor) |
| `ProvisionedThroughput` | Current RU/s setting |
| `ThrottleRate` / `429` count | Throttling frequency |
| `ServerSideThrottling` / `ServerSideRequestThrottling` | Server-side throttling events |
| `PartitionKeyRUConsumption` / `PartitionKeyStorage` | Hot partition / skew evidence |
| `DataUsage` / `IndexUsage` | Storage pressure |
| `AvailableStorage` | Approaching physical partition limit |
| `TotalRequestCount` | Volume and latency classification |
| `MongoRequests` / `CassandraRequests` | API-specific request/Throttle stats |

Verify exact metric names with `az monitor metrics list-definitions` for the target account.

## Common Architectures

### Single-Region, Manual RU/s

Simplest. Cheapest but no regional failover; RU/s fixed.

### Multi-Region with Multi-Region Writes

Replicated write regions. Lower write latency per region but raises conflict-resolution complexity and RU cost (each region consumes its own RU/s). Changing this in production needs confirmation.

### Autoscale vs Manual

Autoscale suits spiky workloads; manual suits steady, cost-sensitive workloads. Switching modes is a documented, confirm-gated change.

## Delegation Boundaries

| Need | Delegate |
|------|----------|
| Cost analysis | `azure-cost-ops` |
| Generic Azure Monitor KQL/alert management | `azure-monitor-ops` |
| RBAC, Activity Log, locks, policy-only work | `azure-audit-ops` |
| Private endpoint / private DNS design | `azure-privateendpoint-ops` |
| Data-plane query rewrite (SQL/Mongo statements) | DBA/app owner; this skill reports evidence and recommendations |
