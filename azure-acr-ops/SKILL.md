---
name: azure-acr-ops
description: >-
  Use when operating or diagnosing Azure Container Registry. User mentions ACR,
  registry, repository, image tag, manifest, import, purge, ImagePullBackOff,
  AcrPull, managed identity image pulls, registry firewall, private endpoint,
  or ACR AIOps/RCA.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials,
  network access to Azure management endpoints and registry endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-06-09"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Container Registry Operations Skill

## Overview

Azure Container Registry stores and distributes container images and OCI artifacts. This skill handles registry operations, image/repository diagnostics, AKS pull failure RCA, network/auth troubleshooting, and AIOps-assisted incident analysis. Keep this file concise; load references for commands, SDK patterns, RCA rules, and detailed scenarios.

## Trigger & Scope

### SHOULD Use When
- User mentions ACR, Azure Container Registry, image push/pull, repository, tag, manifest, import, purge, retention, quarantine, or registry token.
- Task involves registry create/show/list/update/delete, repository/tag/manifest inspection, image delete/import, identity/RBAC, firewall/private endpoint, or diagnostic logs.
- User asks for AKS `ImagePullBackOff` / `ErrImagePull` RCA involving ACR authentication, image existence, or network access.
- User asks for AIOps analysis, anomaly detection, pull failure spike, auth failure spike, repository growth, or incident timeline.

### SHOULD NOT Use When
- Kubernetes pod/node/cluster health beyond image pull evidence → delegate to `azure-aks-ops`.
- Billing/cost only → delegate to `azure-cost-ops`.
- Generic Monitor query/alert authoring → delegate to `azure-monitor-ops`.
- RBAC or Activity Log-only audit → delegate to `azure-audit-ops`.
- Application image build/Dockerfile optimization → report registry evidence; app/build owners change code.

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; required for registry operations |
| `{{user.location}}` | User input | Azure Location, e.g. `eastus`; validate before create |
| `{{user.registry_name}}` | User input | ACR registry name |
| `{{user.repository}}` | User input | Repository name, e.g. `app/api` |
| `{{user.tag}}` | User input | Image tag |
| `{{user.digest}}` | User input | Manifest digest |
| `{{user.analysis_window}}` | User input | Default `PT1H`; use `PT6H`/`P1D` for incidents |
| `{{output.registry_id}}` | CLI/SDK output | Parse from `.id` |
| `{{output.login_server}}` | CLI/SDK output | Parse from `.loginServer` |

## JSON Paths

```yaml
REGISTRY_ID: id
LOGIN_SERVER: loginServer
PROVISIONING_STATE: provisioningState
ADMIN_ENABLED: adminUserEnabled
PUBLIC_NETWORK_ACCESS: publicNetworkAccess
NETWORK_RULE_SET: networkRuleSet
PRIVATE_ENDPOINTS: privateEndpointConnections[].privateEndpoint.id
```

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover → Report**.

| Phase | Required Actions |
|-------|------------------|
| Pre-flight | Verify CLI, credentials, subscription, Resource Group, Location, provider, RBAC, registry state, and target repository/tag/digest. |
| Execute | Use Azure CLI primary. Retry transient CLI failures up to 3x with backoff before SDK fallback. |
| Validate | Confirm registry/image state with `--output json`; poll LRO every 30s, max 30m unless reference says otherwise. |
| Recover | Apply HALT-vs-retry matrix; never guess manifest/tag fields or repeat destructive deletes blindly. |
| Report | Return evidence, confidence, safe next actions, owner-review items, and actions requiring confirmation. |

## Operation Map

| Intent | Primary CLI | Reference |
|--------|-------------|-----------|
| Registry create/show/list/update/delete | `az acr` | [integration.md](references/integration.md) |
| Repository/tag/manifest inspect/delete | `az acr repository` / `az acr manifest` | [integration.md](references/integration.md) |
| Image import/retag/purge/retention | `az acr import`, `az acr run`, `acr purge` | [integration.md](references/integration.md) |
| AKS pull failure RCA | ACR evidence + AKS handoff | [troubleshooting.md](references/troubleshooting.md) |
| Auth/RBAC/network diagnostics | RBAC, token, firewall, private endpoint, DNS | [troubleshooting.md](references/troubleshooting.md) |
| AIOps incident analysis | Metrics/logs/activity correlation | [aiops.md](references/aiops.md) |

## Safety Gates

Require explicit human confirmation with exact registry name and Resource Group before:
- delete registry, repository, manifest, tag, or OCI artifact;
- purge images or change retention/quarantine policy affecting production repositories;
- enable admin user, regenerate credentials, or create/delete tokens/passwords;
- change public network access, firewall allowlists, trusted services, or private endpoint approval;
- import/overwrite tags used by production deployments.

If confirmation is missing or user asks to skip it, HALT and explain the required confirmation.

## AIOps and RCA Rules

Use AIOps only for observation, correlation, diagnosis, and recommendations. Do not auto-remediate. Load [aiops.md](references/aiops.md) for pull failures, auth failures, network failures, push/pull latency, storage growth, purge/retention issues, or unknown incident cause.

RCA output must include: symptom, timeline, registry/image evidence, identity/network evidence, likely root causes, confidence, safe checks, approval-required actions, owner-review items, and escalation criteria.

## Recovery Matrix

| Condition | Agent Action |
|-----------|--------------|
| AuthorizationFailed / AcrPull missing | HALT; report required RBAC from [integration.md](references/integration.md) |
| Registry/repository/tag/digest not found | HALT; verify name, Resource Group, subscription, repository, tag/digest |
| InvalidLocation / SKU unavailable | HALT; validate Location/SKU and suggest supported options |
| Network denied / private DNS mismatch | HALT mutation; collect network evidence and escalate to network owner |
| Throttling / 429 | Backoff and retry up to 3x |
| 5xx / transient network | Retry up to 3x, then HALT with correlation ID |
| Destructive action without confirmation | HALT; require explicit confirmation |

## Quality Gate

GCL is required for destructive/disruptive operations and recommended for incident RCA. Use [rubric.md](references/rubric.md) and [prompt-templates.md](references/prompt-templates.md). Rubric dimensions: correctness, safety, idempotency, traceability, spec compliance, RCA quality. Safety score `0` aborts immediately.

Persist GCL traces to `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` with secrets masked as `***`.

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Integration and Commands](references/integration.md)
- [Troubleshooting and RCA](references/troubleshooting.md)
- [AIOps Analysis](references/aiops.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

