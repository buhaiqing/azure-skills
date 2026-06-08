# Azure Container Registry Core Concepts

## Resource Identity

Use full resource IDs in reports and traces:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.ContainerRegistry/registries/{{user.registry_name}}
```

## Key Concepts

| Concept | Meaning | Operational Impact |
|---------|---------|--------------------|
| Registry | ACR resource containing repositories and artifacts | Main resource controlled by `az acr` |
| Login server | Registry endpoint such as `{{user.registry_name}}.azurecr.io` | Used by Docker/AKS pulls |
| Repository | Image namespace such as `app/api` | Contains tags and manifests |
| Tag | Mutable image label | Can be moved; digest is stronger evidence |
| Manifest digest | Immutable content reference | Best for deployment provenance |
| SKU | Basic, Standard, Premium | Network, throughput, retention, geo-replication features vary |
| Admin user | Registry-level username/password auth | High-risk; prefer managed identity/RBAC |
| Token/scope map | ACR repository-scoped auth | Credential lifecycle must be controlled |
| Private endpoint | Private connectivity to registry | Requires Private DNS and VNet access |
| Firewall rules | Public endpoint allowlist | Broad access increases exposure |
| Retention/purge | Image lifecycle management | Can break rollback if production tags are deleted |
| Quarantine/content trust | Image governance controls | Can block image pulls or promotions |

## Common Identity Models

| Model | Use Case | Notes |
|-------|----------|-------|
| AKS kubelet managed identity + AcrPull | Preferred AKS pull model | Assign `AcrPull` on registry scope |
| Service principal | Legacy automation | Secret rotation required; avoid in reports |
| Admin user | Emergency/simple auth | Disabled by default in secure environments |
| Repository token | Scoped automation | Manage token/password rotation carefully |

## Metrics and Logs

| Signal | Use |
|--------|-----|
| Registry login/pull/push logs | Auth and image access RCA |
| Activity Log | Registry/network/RBAC/config change timeline |
| Storage usage | Growth anomaly and cleanup planning |
| Pull/push failure patterns | Outage and workload impact |
| Private endpoint state | Network access RCA |

Metric/log names vary by diagnostic configuration. Verify with Azure Monitor and diagnostic settings before final claims.

## AKS Boundary

This skill diagnoses ACR-side evidence for `ImagePullBackOff` and `ErrImagePull`:
- image exists by repository/tag/digest;
- AKS identity has `AcrPull`;
- registry network allows cluster path;
- logs show auth/network/not-found failures.

Delegate pod scheduling, node DNS runtime, kubelet health, and cluster lifecycle to `azure-aks-ops`.

## Delegation Boundaries

| Need | Delegate |
|------|----------|
| AKS cluster/pod/node internals | `azure-aks-ops` |
| Generic Monitor KQL/alerts | `azure-monitor-ops` |
| RBAC audit, locks, policy-only work | `azure-audit-ops` |
| Cost analysis | `azure-cost-ops` |
| Deep VNet/Private DNS design | network owner after this skill provides entry diagnostics |
| Dockerfile/build optimization | build/app owner |
