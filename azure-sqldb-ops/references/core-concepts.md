# Azure SQL Database Core Concepts

## Supported Scope

This skill targets **Azure SQL Database**:
- **Logical server** — the parent resource hosting databases (`<name>.database.windows.net`).
- **Single database** — standalone DB with its own service objective (compute).
- **Elastic pool** — shared compute across multiple databases.
- **Managed Instance** — treated read-only here: this skill provides entry diagnostics only and delegates deep MI operations.

SQL Server on Azure VM, Azure Synapse dedicated SQL pool, and PostgreSQL/MySQL are **out of scope**.

## Resource Identity

Use full resource IDs in reports and traces:

```text
# Logical server
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Sql/servers/{{user.server_name}}

# Database
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Sql/servers/{{user.server_name}}/databases/{{user.database_name}}

# Elastic pool
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Sql/servers/{{user.server_name}}/elasticPools/{{user.elastic_pool_name}}
```

## Key Concepts

| Concept | Meaning | Operational Impact |
|---------|---------|--------------------|
| Logical server | Parent container for DBs/pools; holds firewall, AAD admin, networking | Delete = all child DBs lost; firewall lives at server scope |
| Single database | DB with own service objective | Scale = change service objective or Max Size |
| Elastic pool | Shared eDTU/vCore across DBs | Pool scale affects all member DBs; per-DB `maxSizeBytes` caps |
| Managed Instance | Isolated SQL engine (IaaS-like) | Out of active scope; entry diagnostics only |
| Service objective (SLO) | Compute tier: DTU (`S0`–`S12`, `P1`–`P15`) or vCore (`GP_Gen5_4`, `BC_Gen5_8`, `HS_Gen5_8`) | Determines cost, perf, HA model |
| DTU vs vCore | DTU bundles CPU/IO/memory; vCore maps to cores directly | vCore preferred for transparency; DTU simpler for small DBs |
| Max Size | Per-DB storage cap (`maxSizeBytes`) | Shrinking (lower than used) is blocked; growth is safe |
| Transparent Data Encryption (TDE) | Encryption at rest, on by default | Cannot disable on some tiers; affects backup/restore |
| Firewall rules | Server-scoped IP allowlist + Azure-services toggle | Narrow rules only; `0.0.0.0` broad exposure is risky |
| Private endpoints | VNet-integrated private access | DNS, subnet, and NSG affect connectivity |
| Automatic tuning | Azure auto-index/plan correction (`FORCE_LAST_GOOD_PLAN`, `CREATE_INDEX`) | Auto-plan-forcing recommended; auto-index needs DBA review |
| Query Store | Per-DB query plan/performance history | Required for high-confidence slow-query RCA |
| Retention/backup | PITR + long-term retention (LTR) | Determines restore options; delete is irreversible |

## Compute Models

### DTU model
- Tiers: Basic, Standard (`S0`–`S12`), Premium (`P1`–`P15`).
- Single bundle of compute/IO/memory; simpler sizing, less granularity.

### vCore model
- Tiers: General Purpose (`GP_Gen5_n`), Business Critical (`BC_Gen5_n`), Hyperscale (`HS_Gen5_n`).
- Per-DB or elastic-pool; hardware gen (`Gen5`), and explicit vCore count.
- Hyperscale scales storage independently and reads from replicas.

## Operational States

| State | Meaning | Action |
|-------|---------|--------|
| Ready / Online | Server/DB can accept operations | Continue |
| Scaling / Updating | Long-running compute/Max Size change in progress | Poll; do not start another mutation |
| Paused / Stopped | Server compute stopped (serverless/`az sql server stop`) | Start requires confirmation in production |
| Inaccessible / ProvisioningFailed | Control-plane or billing/security issue | HALT and investigate |

## Metrics Used for Operations

| Metric | Signal |
|--------|--------|
| `dtu_consumption_percent` | DTU saturation (DTU model) |
| `cpu_percent` | vCore CPU saturation |
| `storage_percent` | Storage exhaustion risk (shared with data/max size) |
| `storage` / `allocated_data_storage` | Absolute storage used |
| `connection_successful` / `connection_failed` | Auth/firewall/network connectivity |
| `sessions_percent` | Session-pool/connection pressure |
| `workers_percent` | Worker-thread pressure |
| `deadlock` | Transaction contention |
| `blocked_by_firewall` | Firewall-blocking evidence |
| `tempdb_log_size` / `tempdb_log_used_percent` | Tempdb/transaction-log pressure |

Verify exact metric names with `az monitor metrics list-definitions` for the target resource (server-scoped metrics vs database-scoped metrics differ).

## Common Architectures

### Public Access with Firewall

Server has a public FQDN; access controlled by server firewall rules + "Allow Azure services" toggle. Validate rules are narrow; avoid `0.0.0.0/0` or start/end `0.0.0.0`.

### Private Access (Private Endpoint)

Preferred for production. Check:
- private endpoint + private DNS zone (`privatelink.database.windows.net`) linkage;
- client VNet DNS resolution;
- NSG / route table on the client subnet;
- server public network access disabled if policy requires private-only.

### Elastic Pool Pattern

Multiple DBs share eDTU/vCore. A noisy neighbor in the pool can starve others; pool scale is a shared-risk change.

### HA and Backups

- Zone-redundant / Business Critical provides local replicas; failover is Azure-managed.
- PITR and LTR define restore options. Restore creates a **new** DB/server; overwriting is not a safe default.

## Delegation Boundaries

| Need | Delegate |
|------|----------|
| Cost analysis | `azure-cost-ops` |
| Generic Azure Monitor KQL/alert management | `azure-monitor-ops` |
| RBAC, Activity Log, locks, policy-only work | `azure-audit-ops` |
| Deep VNet/Private DNS design | network owner after this skill provides entry diagnostics |
| Data Factory / Synapse / pipeline movement | relevant data-movement skill |
| T-SQL rewrite, index creation, DDL execution | DBA/app owner; this skill reports evidence and recommendations |
