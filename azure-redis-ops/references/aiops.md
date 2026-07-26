# Azure Redis AIOps Analysis

## Purpose

AIOps in this skill means metric anomaly detection, evidence correlation, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Inputs

| Input | Source |
|-------|--------|
| Resource state | `az redis show` |
| Metrics | Azure Monitor metrics |
| Activity timeline | Activity Log, delegate deep audit to `azure-monitor-ops` (see `docs/cross-skill-rca-schema.md`) |
| Diagnostic logs | Log Analytics if enabled; delegate complex KQL to `azure-monitor-ops` |
| User incident context | symptom, start time, impacted clients, recent deploys |
| Client-side evidence | app logs, timeout/auth error samples, connection pool stats |

## Analysis Windows

| Window | Use |
|--------|-----|
| `PT1H` | Active incident, high-resolution triage |
| `PT6H` | Incident evolution and recent changes |
| `P1D` | Daily pattern, scale decision support |
| Baseline same hour previous day/week | Avoid false positives from normal traffic cycles |

## Metric Collection

```bash
az monitor metrics list \
  --resource "{{output.redis_id}}" \
  --metric "usedmemorypercentage,serverload,connectedclients,cachehits,cachemisses,evictedkeys,operationsPerSecond,cacheRead,cacheWrite" \
  --interval PT1M \
  --aggregation Average,Maximum,Total \
  --start-time "{{user.start_time}}" \
  --end-time "{{user.end_time}}" \
  --output json
```

If exact metrics differ by SKU, query definitions first and map equivalent metrics.

## Detection Signals

| Signal | Source | Threshold | Severity |
|--------|--------|-----------|----------|
| redis_memory_pressure | `az monitor metrics list` --metric "usedmemorypercentage" | > 80% sustained for > 5min | High |
| redis_connection_exhaustion | `az monitor metrics list` --metric "connectedclients" | > 90% of maxclients limit | High |
| redis_cpu_overload | `az monitor metrics list` --metric "serverload" | > 80% sustained for > 5min | Medium |
| redis_command_latency | `az monitor metrics list` --metric "operationsPerSecond" + "cachehits/cachemisses" | Latency > 100ms or hit rate drop > 15% | Medium |
| redis_eviction_burst | `az monitor metrics list` --metric "evictedkeys" | evictedkeys > 0 when baseline is 0 | High |
| redis_replication_lag | `az redis show` --query "replicationRole" + metrics | Replication lag > 10s or sync failures | Medium |
| redis_cache_hit_rate_drop | `az monitor metrics list` --metric "cachehits", "cachemisses" | Hit rate drops > 15 percentage points | Medium |

## Anomaly Rules

| Signal | Detection Rule | Root-Cause Candidates |
|--------|----------------|-----------------------|
| Memory pressure | current memory > baseline by 30% or sustained > 80% | capacity, TTL, large keys, fragmentation |
| Eviction burst | evictedkeys > 0 when baseline is 0, or sharp increase | maxmemory pressure, policy mismatch |
| Hit rate drop | hit rate drops > 15 percentage points | cache warming, key namespace change, expiry storm |
| Client spike | connectedclients > 2x baseline | pool leak, traffic surge, deploy bug |
| Server load high | serverload sustained high with ops/sec spike | hot key, slow command, CPU pressure |
| Bandwidth high | cacheRead/cacheWrite > 2x baseline | large values, read amplification |
| Auth failures after change | errors rise after key rotation/config update | stale secret, TLS/auth mismatch |

## RCA Rules

### Rule 1: Memory Pressure / Eviction Crisis
- **Trigger**: redis_memory_pressure > 80% OR redis_eviction_burst detected
- **Diagnostic Steps**:
  1. Check current memory usage and eviction policy: `az redis show --query "properties.redisConfiguration.maxmemory-policy"`
  2. Identify large keys using Redis CLI: `redis-cli --bigkeys` (requires access)
  3. Check TTL configuration: `redis-cli ttl <key>` for sample keys
  4. Monitor eviction rate: `az monitor metrics list --metric "evictedkeys"`
  5. Check for memory fragmentation: `redis-cli info memory | grep fragmentation`
- **Root Causes**:
  - Insufficient capacity for workload
  - Missing or incorrect TTL causing key accumulation
  - Large individual keys consuming disproportionate memory
  - Memory fragmentation > 1.5
  - Volatile eviction policy too aggressive
- **Resolution**:
  - Short-term: Scale up tier or adjust maxmemory-policy
  - Long-term: Implement TTL strategy, optimize key size, consider clustering
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的缓存层诊断路径

### Rule 2: Connection Pool Exhaustion
- **Trigger**: redis_connection_exhaustion > 90% of maxclients limit
- **Diagnostic Steps**:
  1. Check current connections: `az redis show --query "properties.redisConfiguration.maxclients"`
  2. Monitor connection metrics: `az monitor metrics list --metric "connectedclients"`
  3. Check client connection patterns in app logs (if available)
  4. Identify idle connections: `redis-cli client list` (requires access)
  5. Check for connection leaks in application code
- **Root Causes**:
  - Connection pool size too large in application
  - Application not properly releasing connections
  - Connection timeout misconfigured
  - Sudden traffic spike exceeding expected capacity
  - Multiple applications sharing same cache instance
- **Resolution**:
  - Adjust maxclients limit if SKU supports it
  - Fix connection leak in application code
  - Implement connection pooling with proper timeout
  - Consider separate cache instances per application
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的应用层诊断路径

### Rule 3: CPU Overload and Command Latency
- **Trigger**: redis_cpu_overload > 80% OR redis_command_latency > 100ms
- **Diagnostic Steps**:
  1. Identify slow commands: `redis-cli slowlog get 10` (requires access)
  2. Check command distribution: `redis-cli info stats | grep instantaneous_ops_per_sec`
  3. Monitor server load: `az monitor metrics list --metric "serverload"`
  4. Check for expensive operations (KEYS, SCAN, large SORT)
  5. Analyze network bandwidth: `az monitor metrics list --metric "cacheRead", "cacheWrite"`
- **Root Causes**:
  - Expensive commands (KEYS, full SCAN, large SORT operations)
  - Hot keys causing disproportionate command volume
  - Insufficient CPU capacity for command rate
  - Large value sizes causing network/processing overhead
  - Lua scripts with long execution time
- **Resolution**:
  - Replace KEYS with SCAN, avoid large SORT operations
  - Implement hot key sharding or caching at app layer
  - Scale up to higher tier with more CPU
  - Optimize value sizes (compression, normalization)
  - Optimize Lua scripts to avoid long blocking
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的性能层诊断路径

### Rule 4: Replication Lag and Sync Issues
- **Trigger**: redis_replication_lag > 10s OR sync failures in logs
- **Diagnostic Steps**:
  1. Check replication status: `az redis show --query "properties.replicationRole"`
  2. Monitor replication metrics in Azure Monitor
  3. Check network bandwidth between master and replica
  4. Examine Redis logs for sync errors: `az redis show --query "properties.instances"`
  5. Check for write burst during sync: `az monitor metrics list --metric "cacheWrite"`
- **Root Causes**:
  - Network bandwidth insufficient for write volume
  - Master write rate exceeds replica sync capacity
  - Network partition or latency issues
  - Replica under-provisioned
- **Resolution**:
  - Reduce write burst during sync windows
  - Scale up to tier with higher network bandwidth
  - Check Azure network health and private endpoint configuration
  - Consider multiple replicas for read scaling
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的数据层诊断路径

### Rule 5: Cache Hit Rate Drop
- **Trigger**: redis_cache_hit_rate_drop > 15 percentage points
- **Diagnostic Steps**:
  1. Calculate current hit rate: `hits / (hits + misses) * 100`
  2. Check for expiry storm: `az monitor metrics list --metric "evictedkeys", "expiredkeys"`
  3. Analyze key namespace changes in application logs
  4. Check for cache warming failure after deployment
  5. Monitor traffic pattern changes: `az monitor metrics list --metric "operationsPerSecond"`
- **Root Causes**:
  - Recent deployment changed key namespace
  - Cache warming failure after restart/deployment
  - TTL expiry storm (many keys expiring simultaneously)
  - Query pattern change accessing different key space
  - Eviction policy removing frequently accessed keys
- **Resolution**:
  - Implement cache warming after deployments
  - Stagger TTL values to avoid expiry storms
  - Review eviction policy (LRU vs LFU vs volatile)
  - Pre-load critical keys after deployment
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md`,关联 `azure-monitor-ops`（诊断日志）、`azure-sqldb-ops`、`azure-postgres-ops`、`azure-cosmos-ops`（缓存一致性）

## Correlation Rules

### Change Correlation

If anomaly start is within 30 minutes after an Activity Log event, increase confidence for that event as a cause.

High-risk change categories:
- key regeneration;
- reboot;
- scale/update;
- firewall/private endpoint update;
- TLS/non-SSL config change;
- app deployment reported by user.

### Dependency Correlation

If cache miss rate increases and backend database latency/CPU also increases, classify as possible cache stampede or cache warming failure. Redis alone cannot prove this; ask for backend metrics or delegate to `azure-sqldb-ops`, `azure-postgres-ops`, or `azure-cosmos-ops` based on database type.

### Network Correlation

If server metrics are normal but client timeouts rise, prioritize DNS, firewall, TLS, route, and client connection pool checks over cache scaling.

## Confidence Scoring

| Level | Requirement |
|-------|-------------|
| High | Two or more independent evidence sources agree, and timeline matches |
| Medium | Metrics match symptom and timeline, but logs/client evidence are missing |
| Low | Single signal or weak timing; more evidence needed |

Never present low-confidence hypotheses as facts.

## Risk-Ranked Recommendation Model

| Risk | Examples | Agent Behavior |
|------|----------|----------------|
| Safe | read metrics, show config, list firewall rules, query Activity Log | execute directly |
| Low | enable additional diagnostic collection when non-disruptive | ask if cost/noise impact unclear |
| Medium | scale up, narrow firewall change, config update | require confirmation and rollback note |
| High | delete, flush, reboot, regenerate keys, scale down, broaden firewall | require explicit confirmation; use GCL |

## AIOps Report Template

```text
Incident: <short title>
Window analyzed: <start/end + baseline>
Anomalies:
- <metric>: <observed> vs <baseline>, time <window>
Correlations:
- <Activity Log/config/app event> within <minutes> of anomaly
Root-cause candidates:
1. <candidate> — Confidence: High|Medium|Low — Evidence: <evidence>
2. <candidate> — Confidence: High|Medium|Low — Evidence: <evidence>
Safe checks completed:
- <command/result summary>
Recommended next actions:
- Safe: <diagnostic>
- Approval required: <operation + impact>
Escalation:
- <team/support condition>
```

## Guardrails

- Do not claim causality from correlation alone.
- Do not run destructive/disruptive commands as part of AIOps.
- Do not expose access keys, connection strings, or secrets in reports.
- Mask any accidentally returned credential-like value as `***`.
- If evidence is insufficient, state what evidence is missing.

## Cross-Skill Integration

- 相关 Skill: azure-monitor-ops（诊断日志、Activity Log）、azure-sqldb-ops、azure-postgres-ops、azure-cosmos-ops（缓存一致性）
- 标准诊断路径: 参考 `docs/cross-skill-rca-schema.md` 的跨服务根因分析链
- 协作场景:
  - 缓存失效导致数据库负载升高 → 协调 azure-monitor-ops + 数据库 skill
  - 应用层连接问题 → 需要客户端日志或网络 skill 协助
  - 安全/认证问题 → 可能需要 azure-keyvault-ops（密钥轮换）或网络安全 skill
