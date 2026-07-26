# Azure Key Vault AIOps Analysis

## Detection Signals

| Signal | Source | Threshold | Severity |
|--------|--------|-----------|----------|
| access_denied_spike | `az monitor activity-log list` + diagnostic logs (AuditEvent) | 403/401 count > 2x baseline within PT1H | High |
| request_throttling | diagnostic logs (AuditEvent) + Azure Monitor metrics | 429 responses > 0 within PT1H | Medium |
| certificate_near_expiry | `az keyvault certificate list` + `az keyvault certificate show` | expires within P30D | High |
| secret_version_churn | `az keyvault secret list-versions` | > 10 new versions within PT1H | Medium |
| key_operation_failure | `az monitor activity-log list` + vault diagnostic logs | crypto operation failures > 0 within PT1H | High |
| firewall_block | `az monitor activity-log list` + network diagnostic logs | timeout/forbidden with valid permissions | Critical |

## Purpose

AIOps in this skill means anomaly detection, identity/network/object lifecycle correlation, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Inputs

| Input | Source |
|-------|--------|
| Vault state/config | `az keyvault show` |
| Object metadata | secret/key/certificate metadata only |
| Diagnostic logs | Azure Monitor / Log Analytics if enabled |
| Activity timeline | Activity Log, delegate deep audit to `azure-monitor-ops` (see `docs/cross-skill-rca-schema.md`) |
| App error context | user-provided error excerpts, identity, request timing |
| Certificate inventory | certificate expiry attributes and policy metadata |

## Analysis Windows

| Window | Use |
|--------|-----|
| `PT1H` | Active access outage |
| `PT6H` | Identity/network/config correlation |
| `P30D` | certificate expiry and unusual operation trend |
| Baseline same hour previous day/week | Avoid normal traffic-cycle false positives |

## RCA Rules

### Rule 1: Access Denied Root Cause
- **Trigger**: access_denied_spike detected (403/401 > 2x baseline)
- **Diagnostic Steps**:
  1. Check vault access policy: `az keyvault show --name <vault> --query properties.accessPolicies`
  2. Check RBAC assignments: `az role assignment list --scope <vault-resource-id>`
  3. Verify caller identity: `az ad sp show --id <caller-object-id>` or `az ad user show --id <caller-object-id>`
  4. Check tenant mismatch: compare vault tenant vs caller tenant ID
  5. Cross-reference with Activity Log for permission changes
- **Root Causes**:
  - Missing or incorrect RBAC role / access policy entry
  - Caller identity deleted or disabled
  - Tenant mismatch (multi-tenant scenario)
  - Access policy recently removed or modified
- **Resolution**: Grant appropriate RBAC role (Key Vault Secrets User, Key Vault Crypto User, etc.) or add access policy entry. Confirm identity active and tenant alignment.
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 2: Request Throttling Diagnosis
- **Trigger**: request_throttling detected (429 responses > 0)
- **Diagnostic Steps**:
  1. Check request rate: `az monitor metrics list --resource <vault-id> --metric "ServiceApiHit"`
  2. Identify top callers: query diagnostic logs for caller identity frequency
  3. Check if burst from single app: correlate with app deployment timeline
  4. Review vault throttle limits: `az keyvault show --name <vault> --query properties`
- **Root Causes**:
  - Application retry storm without exponential backoff
  - Multiple apps hitting same vault simultaneously
  - Design issue: vault used as configuration store for high-frequency reads
- **Resolution**: Implement client-side retry with exponential backoff. Distribute load across multiple vaults if sustained. Consider caching at application layer.
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 3: Certificate Expiry Investigation
- **Trigger**: certificate_near_expiry detected (expires within P30D)
- **Diagnostic Steps**:
  1. Check certificate status: `az keyvault certificate show --vault-name <vault> --name <cert>`
  2. Check auto-renewal policy: `az keyvault certificate show --vault-name <vault> --name <cert> --query policy`
  3. Verify issuer configuration: `az keyvault certificate issuer show --vault-name <vault> --name <issuer>`
  4. Check Activity Log for renewal attempts: `az monitor activity-log list --resource <vault-id> --caller "AzureKeyVault"`
  5. Contact certificate owner (from tags or app team)
- **Root Causes**:
  - Auto-renewal disabled or misconfigured
  - Issuer unavailable or credentials expired
  - Manual renewal process gap (owner not notified)
  - Certificate used beyond intended lifecycle
- **Resolution**: Enable auto-renewal if issuer supports it. If manual, trigger renewal with owner confirmation. Update certificate monitoring threshold.
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 4: Firewall/Network Block Diagnosis
- **Trigger**: firewall_block detected (timeout/forbidden with valid permissions)
- **Diagnostic Steps**:
  1. Check vault network rules: `az keyvault show --name <vault> --query properties.networkAcls`
  2. Check private endpoint status: `az network private-endpoint list --resource-group <rg> --query "[?contains(privateLinkServiceConnections[].privateLinkServiceId, '<vault-id>')]"`
  3. Verify caller IP: cross-reference with allowed IP ranges in network rules
  4. Check DNS resolution: `nslookup <vault-name>.vault.azure.net` vs private endpoint IP
  5. Validate private endpoint connection state: `az network private-endpoint-connection list --name <vault>`
- **Root Causes**:
  - Vault firewall enabled but caller IP not in allowlist
  - Private endpoint required but caller using public endpoint
  - DNS misconfiguration pointing to wrong endpoint
  - Private endpoint connection not approved or in failed state
- **Resolution**: Add caller IP to allowlist (if authorized). Fix DNS to resolve private endpoint IP. Approve or repair private endpoint connection.
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径；delegate network diagnostics to `azure-network-ops` (future skill)

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

## Cross-Skill Integration
- 相关 Skill: `azure-monitor-ops`（诊断日志、Activity Log 深度分析）
- 相关 Skill: `azure-network-ops`（私有端点、防火墙、DNS 诊断，future skill）
- 标准诊断路径: `docs/cross-skill-rca-schema.md`

## Guardrails

- Do not run delete/purge/secret overwrite/key rotation/access changes as part of AIOps.
- Do not request or print secret values, private keys, certificates with private material, tokens, or connection strings.
- Mask credential-like values as `***`.
- Do not claim app root cause without app-side identity/error evidence.
- If evidence is insufficient, state what evidence is missing.
