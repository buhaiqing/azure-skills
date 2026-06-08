# Azure Redis AIOps Analysis

## Purpose

AIOps in this skill means metric anomaly detection, evidence correlation, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Inputs

| Input | Source |
|-------|--------|
| Resource state | `az redis show` |
| Metrics | Azure Monitor metrics |
| Activity timeline | Activity Log, delegate deep audit to `azure-audit-ops` |
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

If cache miss rate increases and backend database latency/CPU also increases, classify as possible cache stampede or cache warming failure. Redis alone cannot prove this; ask for backend metrics or delegate to the relevant database skill.

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
