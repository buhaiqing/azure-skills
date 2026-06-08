# Azure Container Registry AIOps Analysis

## Purpose

AIOps in this skill means anomaly detection, ACR/AKS/activity correlation, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Inputs

| Input | Source |
|-------|--------|
| Registry state/config | `az acr show` |
| Repository/tag metadata | `az acr repository show-tags`, manifest metadata |
| Diagnostic logs | Azure Monitor / Log Analytics if enabled |
| Activity timeline | Activity Log, delegate deep audit to `azure-audit-ops` |
| AKS pull evidence | AKS events from `azure-aks-ops` or user-provided output |
| User incident context | symptom, start time, affected workloads, recent deploys |

## Analysis Windows

| Window | Use |
|--------|-----|
| `PT1H` | Active pull/push outage |
| `PT6H` | Deployment and config-change correlation |
| `P1D` | repository growth and retention trend |
| Baseline same hour previous day/week | Avoid normal deployment-cycle false positives |

## Anomaly Rules

| Signal | Detection Rule | Root-Cause Candidates |
|--------|----------------|-----------------------|
| Pull failures spike | failures > 2x baseline or sudden nonzero | missing image, AcrPull, firewall, private DNS |
| Auth failures spike | unauthorized/denied errors increase | missing role, stale secret, token scope, admin disabled |
| Not-found spike | manifest/tag not found errors increase | tag typo, purge, retention, tag overwrite |
| Network failures | timeouts with normal image existence/auth | firewall, private endpoint, DNS, route |
| Repository growth | storage/tag count grows > 30% over baseline | retention gap, CI tag churn, unbounded builds |
| Pull latency | pull duration/errors increase with large images | image size, network path, service issue |

## Correlation Rules

### Change Correlation

If anomaly start is within 30 minutes after an Activity Log or deployment event, increase confidence for that event as a candidate cause.

High-risk change categories:
- RBAC assignment removal/change;
- token/password regeneration;
- admin user disabled/enabled;
- firewall/public network/private endpoint update;
- repository/tag/manifest delete;
- purge/retention policy change;
- deployment image tag change.

### AKS Correlation

If AKS events show `ErrImagePull` and ACR tag exists with valid AcrPull, prioritize network/DNS and cluster runtime evidence. If tag does not exist or AcrPull is missing, prioritize ACR-side root cause.

### Cleanup Correlation

If rollback failure follows purge/delete events and the previous deployment digest no longer exists, classify cleanup policy as likely cause.

## Confidence Scoring

| Level | Requirement |
|-------|-------------|
| High | Image/identity/network evidence and timeline agree |
| Medium | ACR evidence matches symptom but AKS/build/network logs are missing |
| Low | Single signal or weak timing; more evidence needed |

Do not present low-confidence hypotheses as facts.

## Risk-Ranked Recommendation Model

| Risk | Examples | Agent Behavior |
|------|----------|----------------|
| Safe | show registry, list tags, check manifest, query Activity Log | execute directly |
| Low | enable diagnostic collection when non-disruptive | ask if cost/noise impact unclear |
| Medium | assign AcrPull, narrow firewall update, import missing image | require confirmation and owner review |
| High | delete/purge, enable admin user, regenerate token/password, broad firewall, overwrite production tag | require explicit confirmation; use GCL |

## AIOps Report Template

```text
Incident: <short title>
Window analyzed: <start/end + baseline>
Anomalies:
- <pull/auth/not-found/network/storage signal>: <observed> vs <baseline>
Correlations:
- <Activity Log/AKS/build event> within <minutes> of anomaly
Root-cause candidates:
1. <candidate> — Confidence: High|Medium|Low — Evidence: <evidence>
Safe checks completed:
- <command/result summary>
Recommended next actions:
- Safe: <diagnostic>
- Approval required: <operation + impact>
Owner review:
- <AKS/build/security/network item>
Escalation:
- <team/support condition>
```

## Guardrails

- Do not run purge/delete/import-overwrite/credential changes as part of AIOps.
- Do not print tokens, passwords, or docker login credentials.
- Mask credential-like values as `***`.
- Do not claim AKS root cause without AKS-side evidence.
- If evidence is insufficient, state what evidence is missing.
