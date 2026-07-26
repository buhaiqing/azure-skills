# Azure Container Registry AIOps Analysis

## Purpose

AIOps in this skill means anomaly detection, ACR/AKS/activity correlation, root-cause ranking, and risk-ranked recommendations. It must not perform remediation automatically.

## Inputs

| Input | Source |
|-------|--------|
| Registry state/config | `az acr show` |
| Repository/tag metadata | `az acr repository show-tags`, manifest metadata |
| Diagnostic logs | Azure Monitor / Log Analytics if enabled |
| Activity timeline | Activity Log, delegate deep audit to `azure-monitor-ops` (see `docs/cross-skill-rca-schema.md`) |
| AKS pull evidence | AKS events from `azure-aks-ops` or user-provided output |
| User incident context | symptom, start time, affected workloads, recent deploys |

## Analysis Windows

| Window | Use |
|--------|-----|
| `PT1H` | Active pull/push outage |
| `PT6H` | Deployment and config-change correlation |
| `P1D` | repository growth and retention trend |
| Baseline same hour previous day/week | Avoid normal deployment-cycle false positives |

## Detection Signals

| Signal | Source | Threshold | Severity |
|--------|--------|-----------|----------|
| pull_failure_spike | `az monitor metrics list` --metric "PullCount" | failures > 2x baseline or sudden nonzero | High |
| auth_failure_spike | Activity Log + diagnostic logs | unauthorized/denied errors increase > 50% over baseline | High |
| storage_quota_near_limit | `az acr show-usage` | storage usage > 90% of quota | Medium |
| replication_latency_high | `az acr replication list` | sync duration > 10min for geo-replicated registries | Medium |
| webhook_failure_rate | `az acr webhook list` + ping test | failure rate > 5% in last hour | Low |
| not_found_spike | `az monitor metrics list` + diagnostic logs | manifest/tag not found errors > 3x baseline | High |

## Anomaly Rules

| Signal | Detection Rule | Root-Cause Candidates |
|--------|----------------|-----------------------|
| Pull failures spike | failures > 2x baseline or sudden nonzero | missing image, AcrPull, firewall, private DNS |
| Auth failures spike | unauthorized/denied errors increase | missing role, stale secret, token scope, admin disabled |
| Not-found spike | manifest/tag not found errors increase | tag typo, purge, retention, tag overwrite |
| Network failures | timeouts with normal image existence/auth | firewall, private endpoint, DNS, route |
| Repository growth | storage/tag count grows > 30% over baseline | retention gap, CI tag churn, unbounded builds |
| Pull latency | pull duration/errors increase with large images | image size, network path, service issue |

## RCA Rules

### Rule 1: Image Pull Failure
- **Trigger**: pull_failure_spike detected or AKS reports ErrImagePull
- **Diagnostic Steps**:
  1. Verify image exists: `az acr repository show --name <acr> --image <image:tag>`
  2. Check authentication: `az acr show --name <acr> --query anonymousPullEnabled`
  3. Verify AcrPull role: `az role assignment list --assignee <identity> --scope <acr-id>`
  4. Check network path: private endpoint, firewall rules, DNS resolution
  5. Verify AKS cluster identity has AcrPull on ACR
- **Root Causes**:
  - Image/tag does not exist (deleted, typo, retention policy)
  - Missing AcrPull role on AKS cluster identity
  - Firewall blocking access (network security group, firewall rules)
  - Private endpoint DNS misconfiguration
  - Admin user disabled with no AAD integration
- **Resolution**: Fix image reference, assign AcrPull, update firewall rules, or configure private DNS
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径；委托 `azure-aks-ops` 排查集群侧镜像拉取问题

### Rule 2: Authentication/Authorization Failure
- **Trigger**: auth_failure_spike detected or docker login failures
- **Diagnostic Steps**:
  1. Check registry admin user status: `az acr show --name <acr> --query adminUserEnabled`
  2. Verify AAD integration: `az acr show --name <acr> --query identity`
  3. List role assignments: `az role assignment list --scope <acr-id>`
  4. Check token scope and expiry if using ACR tokens
  5. Verify service principal or managed identity credentials
- **Root Causes**:
  - Admin user disabled without AAD fallback
  - Missing or expired AcrPull/AcrPush role assignment
  - Stale service principal secret
  - Token scope insufficient for operation
  - AAD conditional access policy blocking access
- **Resolution**: Enable admin user (if appropriate), assign correct RBAC role, rotate credentials, or adjust token scope
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 3: Storage Quota Exceeded
- **Trigger**: storage_quota_near_limit or push failures with quota error
- **Diagnostic Steps**:
  1. Check current usage: `az acr show-usage --name <acr>`
  2. List repositories by size: `az acr repository list --name <acr>` then `az acr repository show --name <acr> --repository <repo>`
  3. Identify untagged manifests: `az acr manifest list-metadata --name <acr> --repository <repo>`
  4. Check retention policy: `az acr config retention show --registry <acr>`
  5. Review CI/CD tagging strategy for tag churn
- **Root Causes**:
  - No retention policy configured
  - CI/CD generating many unique tags without cleanup
  - Untagged manifests accumulating (orphaned layers)
  - Large base images without layering optimization
- **Resolution**: Configure retention policy, implement tag cleanup in CI/CD, purge untagged manifests, or upgrade tier
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 4: Replication Latency
- **Trigger**: replication_latency_high or geo-replicated pull failures
- **Diagnostic Steps**:
  1. List replication status: `az acr replication list --registry <acr>`
  2. Check replication health: `az acr replication show --registry <acr> --name <region>`
  3. Verify network connectivity between regions
  4. Check for large image pushes that may cause sync delays
  5. Review replication provisioning state
- **Root Causes**:
  - Network bandwidth constraints between regions
  - Large image layers increasing sync time
  - Replication not yet provisioned in new region
  - Azure platform issue in target region
- **Resolution**: Wait for sync completion, optimize image size, check Azure status, or contact support
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

### Rule 5: Webhook Failure
- **Trigger**: webhook_failure_rate elevated
- **Diagnostic Steps**:
  1. List webhooks: `az acr webhook list --registry <acr>`
  2. Test webhook endpoint: `az acr webhook ping --registry <acr> --name <webhook>`
  3. Check webhook configuration: `az acr webhook show --registry <acr> --name <webhook>`
  4. Review diagnostic logs for webhook delivery failures
  5. Verify target endpoint is accessible from ACR
- **Root Causes**:
  - Target endpoint unreachable (network, DNS, firewall)
  - Invalid webhook URL or authentication credentials
  - Target endpoint returning errors (4xx/5xx)
  - Webhook disabled or misconfigured
  - Payload size exceeding endpoint limits
- **Resolution**: Update webhook URL, fix endpoint connectivity, verify credentials, or reconfigure webhook
- **Cross-Skill Integration**: 参考 `docs/cross-skill-rca-schema.md` 的标准诊断路径

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

## Cross-Skill Integration

当检测到涉及其他服务的异常时，按照 `docs/cross-skill-rca-schema.md` 的标准诊断路径进行跨服务协作：

- **azure-monitor-ops**: 诊断日志查询、Activity Log 关联分析、指标趋势可视化
- **azure-aks-ops**: AKS 集群侧镜像拉取问题排查（ErrImagePull、ImagePullBackOff）、kubelet 日志分析、节点网络诊断
- **azure-network-ops**: 私有端点 DNS 配置、防火墙规则、网络安全组诊断（未来 skill）
- **azure-keyvault-ops**: 存储在 Key Vault 中的 ACR 凭证轮换问题（未来 skill）
