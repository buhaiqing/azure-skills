# Azure Redis Core Concepts

## Service Families

| Family | Use Case | Notes |
|--------|----------|-------|
| Azure Cache for Redis Basic/Standard/Premium | General managed Redis cache | Common CLI surface: `az redis` |
| Azure Cache for Redis Enterprise / Enterprise Flash | Larger scale, modules, active geo-replication | CLI surface may use `az redisenterprise` |
| Azure Managed Redis | Newer managed Redis offering where available | Verify CLI support and REST API before mutation |

Always identify the exact resource type before operating. Do not assume Enterprise commands work on non-Enterprise caches.

## Resource Identity

Use full resource IDs in reports and traces:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Cache/Redis/{{user.redis_name}}
```

For Enterprise:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Cache/redisEnterprise/{{user.redis_name}}
```

## Key Concepts

| Concept | Meaning | Operational Impact |
|---------|---------|--------------------|
| SKU | Basic, Standard, Premium, Enterprise family | Determines HA, clustering, persistence, modules, scale options |
| Capacity | Cache size tier | Affects memory, throughput, and price |
| Shard | Partition in clustered/Enterprise caches | Reboot/scale may affect specific shards |
| Access keys | Primary/secondary keys for auth | Regeneration can break clients until rotated |
| TLS / non-SSL port | Secure/insecure connectivity | Disabling TLS or enabling non-SSL is high-risk |
| Firewall rules | Public endpoint IP allowlist | Broad ranges increase exposure |
| Private endpoint | Private connectivity to cache | Depends on Private DNS zone and VNet links |
| Persistence | RDB/AOF-style durability in supported tiers | Changes may affect recovery objectives |
| Eviction policy | How Redis evicts keys under memory pressure | Misfit policy can cause outages or stale data |

## Metrics Used for Operations

| Metric | Signal |
|--------|--------|
| `usedmemorypercentage` / memory usage | Memory pressure and scale triggers |
| `evictedkeys` | Data loss due to eviction pressure |
| `cachehits`, `cachemisses` | Hit rate and application cache efficiency |
| `serverload` | CPU/event-loop pressure |
| `connectedclients` | Client leak or traffic surge |
| `operationsPerSecond` | Workload throughput |
| `cacheRead`, `cacheWrite` | Network bandwidth pressure |
| `errors` | Client/server failures |

Verify exact metric names with `az monitor metrics list-definitions` for the target resource. Do not invent names in final reports.

## Common Architecture Patterns

### Public Endpoint with Firewall

Use only for controlled environments. Validate firewall ranges and TLS.

### Private Endpoint

Preferred for production. Check:
- private endpoint connection state;
- Private DNS zone record;
- VNet link;
- client subnet DNS resolver behavior.

### Zone Redundancy / Replication

Availability options vary by SKU and Location. Confirm support before create/update.

### Cache-aside Application Pattern

Typical app flow: read cache → miss → read database → write cache. Redis incidents often amplify backend database load when hit rate drops.

## Delegation Boundaries

| Need | Delegate |
|------|----------|
| Cost analysis | `azure-cost-ops` |
| Generic Azure Monitor KQL/alert management | `azure-monitor-ops` |
| RBAC, Activity Log, locks, policy-only work | `azure-audit-ops` |
| Deep VNet/Private DNS design | network owner after this skill provides entry diagnostics |
| Application code cache strategy | app owner; this skill reports evidence and recommendations |
