# Azure PostgreSQL Core Concepts

## Supported Scope

This skill targets Azure Database for PostgreSQL Flexible Server. Single Server is retired/legacy in many environments; if encountered, report the limitation and avoid mutation unless the user explicitly confirms the legacy target and supported commands.

## Resource Identity

Use full resource IDs in reports and traces:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.DBforPostgreSQL/flexibleServers/{{user.server_name}}
```

## Key Concepts

| Concept | Meaning | Operational Impact |
|---------|---------|--------------------|
| Flexible Server | Managed PostgreSQL server resource | Main resource controlled by `az postgres flexible-server` |
| Compute SKU | vCore/memory shape | CPU/memory pressure, restart/scale impact |
| Storage | Allocated storage and autogrow behavior | Storage full can stop writes or degrade performance |
| Backup retention | PITR window | Determines restore options |
| High availability | Same-zone or zone-redundant HA where supported | Failover/restart behavior and cost |
| Public access | Firewall-controlled public endpoint | Rules must be narrow; broad access is risky |
| Private access | VNet-integrated private endpoint/private DNS | DNS and subnet configuration affect connectivity |
| Server parameters | PostgreSQL config managed through Azure | Some changes require restart |
| Diagnostic logs | PostgreSQL logs routed to Log Analytics/Event Hub/Storage | Required for slow query and connection RCA |
| Query Store / pg_stat_statements | Query performance evidence | Needed for high-confidence slow-query RCA |

## Operational States

| State | Meaning | Action |
|-------|---------|--------|
| Ready | Server can accept operations | Continue |
| Starting/Stopping/Restarting/Updating | Long-running operation in progress | Poll; do not start another mutation |
| Stopped | Compute stopped | Start requires confirmation in production context |
| Disabled/Inaccessible | Control-plane or billing/security issue | HALT and investigate |

## Metrics Used for Operations

| Metric | Signal |
|--------|--------|
| `cpu_percent` | CPU saturation |
| `memory_percent` | Memory pressure |
| `storage_percent` | Storage exhaustion risk |
| `active_connections` | Connection pool/leak pressure |
| `connections_failed` | Auth/firewall/network failures |
| `iops` / read/write IOPS | Storage pressure or query pattern issue |
| `network_bytes_egress`, `network_bytes_ingress` | Network pressure |
| `deadlocks` | Transaction contention |
| `temp_files` / temp bytes where available | Sort/hash spill pressure |
| `replication_lag` where applicable | Replica/HA issue |

Verify exact metric names with `az monitor metrics list-definitions` for the target server.

## Common Architectures

### Public Access with Firewall

Simple but sensitive. Validate rules are narrow and avoid `0.0.0.0` broad exposure.

### Private Access

Preferred for production. Check:
- delegated subnet / private DNS zone linkage depending on deployment model;
- client VNet DNS resolution;
- route and network security rules;
- server public access disabled if policy requires private-only.

### HA and Backups

HA and backup settings affect recovery options and maintenance windows. Restore operations create a server at a point in time; overwriting data is not a safe default.

## Delegation Boundaries

| Need | Delegate |
|------|----------|
| Cost analysis | `azure-cost-ops` |
| Generic Azure Monitor KQL/alert management | `azure-monitor-ops` |
| RBAC, Activity Log, locks, policy-only work | `azure-audit-ops` |
| Deep VNet/Private DNS design | network owner after this skill provides entry diagnostics |
| SQL rewrite, index creation, DDL execution | DBA/app owner; this skill reports evidence and recommendations |
