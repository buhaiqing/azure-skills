# Azure Key Vault AIOps Analysis

## Purpose

AIOps in this skill means anomaly detection, identity/network/object lifecycle correlation, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Inputs

| Input | Source |
|-------|--------|
| Vault state/config | `az keyvault show` |
| Object metadata | secret/key/certificate metadata only |
| Diagnostic logs | Azure Monitor / Log Analytics if enabled |
| Activity timeline | Activity Log, delegate deep audit to `azure-audit-ops` |
| App error context | user-provided error excerpts, identity, request timing |
| Certificate inventory | certificate expiry attributes and policy metadata |

## Analysis Windows

| Window | Use |
|--------|-----|
| `PT1H` | Active access outage |
| `PT6H` | Identity/network/config correlation |
| `P30D` | certificate expiry and unusual operation trend |
| Baseline same hour previous day/week | Avoid normal traffic-cycle false positives |

## Anomaly Rules

| Signal | Detection Rule | Root-Cause Candidates |
|--------|----------------|-----------------------|
| Denied requests spike | 403/401 > 2x baseline or sudden nonzero | RBAC/access policy, wrong identity, tenant mismatch |
| Network failures | timeout/forbidden with valid permissions | firewall, private endpoint, DNS |
| Certificate near expiry | expires within threshold | renewal failure, owner gap, issuer issue |
| Delete/purge attempts | unusual delete/purge Activity Log entries | operational error, compromise attempt |
| Secret version churn | many versions in short window | deployment loop, automation bug |
| Key operation failures | crypto failures rise | key disabled/expired, permission gap, version drift |
| Unusual operation volume | get/list/set/delete volume > baseline | app loop, outage retry storm, suspicious activity |

## Correlation Rules

### Change Correlation

If anomaly start is within 30 minutes after an Activity Log or deployment event, increase confidence for that event as a candidate cause.

High-risk change categories:
- RBAC assignment change;
- access policy change;
- firewall/public network/private endpoint update;
- secret/key/certificate new version, disable, delete, recover, purge;
- certificate import/merge/issuer update;
- app deployment or identity change reported by user.

### Identity Correlation

If denied requests affect one principal and vault/network metrics are normal, prioritize role/policy/object permission. If many principals fail together, prioritize network, vault config, tenant, or service issue.

### Certificate Correlation

If app TLS/auth failures align with certificate expiry or failed renewal, classify certificate lifecycle as likely cause and escalate to certificate owner.

## Confidence Scoring

| Level | Requirement |
|-------|-------------|
| High | Identity/object/network evidence and timeline agree |
| Medium | Logs/metadata match symptom but app-side identity/error evidence is incomplete |
| Low | Single signal or weak timing; more evidence needed |

Do not present low-confidence hypotheses as facts.

## Risk-Ranked Recommendation Model

| Risk | Examples | Agent Behavior |
|------|----------|----------------|
| Safe | show vault metadata, list object metadata, query Activity Log | execute directly |
| Low | enable diagnostic collection when non-disruptive | ask if cost/noise impact unclear |
| Medium | add narrow role/access policy, renew cert with owner plan, narrow firewall update | require confirmation and security-owner review |
| High | delete/purge, overwrite secret, rotate/delete/disable key, broad firewall, disable protections | require explicit confirmation; use GCL |

## AIOps Report Template

```text
Incident: <short title>
Window analyzed: <start/end + baseline>
Anomalies:
- <denied/network/cert/object signal>: <observed> vs <baseline>
Correlations:
- <Activity Log/app/identity/object event> within <minutes> of anomaly
Root-cause candidates:
1. <candidate> — Confidence: High|Medium|Low — Evidence: <evidence>
Safe checks completed:
- <command/result summary>
Recommended next actions:
- Safe: <diagnostic>
- Approval required: <operation + impact>
Security-owner review:
- <permission/rotation/cert/network item>
Escalation:
- <team/support condition>
```

## Guardrails

- Do not run delete/purge/secret overwrite/key rotation/access changes as part of AIOps.
- Do not request or print secret values, private keys, certificates with private material, tokens, or connection strings.
- Mask credential-like values as `***`.
- Do not claim app root cause without app-side identity/error evidence.
- If evidence is insufficient, state what evidence is missing.
