---
name: azure-aci-ops
description: >-
  Use when operating Azure Container Instances (ACI) resources via Azure CLI or Azure SDK;
  user mentions "Container Instances", "ACI", "container group", "container deployment",
  "serverless container", or ACI operations.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints and container registries.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-07-11"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Container Instances (ACI) Operations Skill

## Overview

Azure Container Instances (ACI) runs containers directly on Azure without managing VMs or orchestrators — ideal for batch jobs, scheduled tasks, and simple serverless container workloads.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure Container Instances", "ACI", "container group", "container deployment"
- Task involves CRUD on **container groups** (create, show, list, restart, delete, stream logs)
- Keywords: aci, container instance, container group, serverless container, az container
- One-off/batch container execution, simple container hosting, dev/test containers

### SHOULD NOT Use When
- Kubernetes orchestration (multi-pod, service mesh, autoscaling) → delegate to: `azure-aks-ops`
- Pushing/building images or ACR registry management (tags, manifests, purge, auth) → delegate to: `azure-acr-ops`
- Private registry auth beyond ACI's own `--registry-*` flags → delegate to: `azure-acr-ops`
- Virtual Network / Private Endpoint / subnet design for ACI → delegate to: `azure-privateendpoint-ops` or `azure-vnet-ops`
- Billing only → delegate to: `azure-cost-ops`
- Generic metrics/alert authoring → delegate to: `azure-monitor-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; required for all ACI ops |
| `{{user.location}}` | User input | Azure Location, e.g. `eastus`; validate before create |
| `{{user.container_group}}` | User input | Container group name; ask once |
| `{{user.container_name}}` | User input | Container name within the group |
| `{{user.image}}` | User input | Container image, e.g. `mcr.microsoft.com/azuredocs/aci-helloworld` |
| `{{output.container_group_id}}` | CLI/SDK output | Parse from `.id` |
| `{{output.ip_address}}` | CLI/SDK output | Parse from `.ipAddress.ip` |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create Container Group

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
<!-- 通用 5 步 Pre-flight 见 [azure-cli-conventions.md#pre-flight-checks-canonical-all-azure--ops-share](../../azure-skill-generator/references/azure-cli-conventions.md#pre-flight-checks-canonical-all-azure--ops-share) -->
| Image pullable | Verify registry access (private → delegate `azure-acr-ops`) | HALT if auth missing |

#### Execute — Azure CLI (Primary)
详见 [references/integration.md](references/integration.md) 的 Quick Reference 和 Private Registry Auth 章节。

#### Execute — Azure SDK (Fallback)
详见 [references/integration.md](references/integration.md)。

### Operation: Show / List

详细 CLI 命令和 SDK 示例见 [references/integration.md](references/integration.md)。

### Operation: Restart

详细 CLI 命令和 SDK 示例见 [references/integration.md](references/integration.md)。

### Operation: Stream Logs

详细 CLI 命令和 SDK 示例见 [references/integration.md](references/integration.md)。

### Operation: Delete Container Group

**Safety Gate**: MUST obtain explicit user confirmation (exact container group name) before deletion. All containers and their local state (ephemeral) are lost.

详细 CLI 命令和 SDK 示例见 [references/integration.md](references/integration.md)。

## GCL Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate. See `AGENTS.md §3–§8`.

| Parameter | Value |
|-----------|-------|
| GCL | **required** |
| max_iterations | 2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE (`az container delete`) → **required**; Safety=0 → ABORT
- CREATE (`az container create`) → **required**; validate pre-flight + idempotency
- RESTART (`az container restart`) → recommended
- SHOW / LIST / LOGS → read-only; optional

## L4 Auto-Feedback Loop

For autonomous operation on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-aci-ops \
  --operation container_create \
  --command "az container create --name {{user.container_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"provisioningState": "Succeeded"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (container_create): auto-feedback loop active
- **Risky operations** (delete): always bypass loop and require explicit human confirmation
- Healing policy: see [`scripts/self_healing/aci_heal.json`](../../scripts/self_healing/aci_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Container Instances Documentation](https://docs.microsoft.com/azure/container-instances/)
- [Azure CLI Container Reference](https://docs.microsoft.com/cli/azure/container)
- [Azure SDK ContainerInstance Module](https://docs.microsoft.com/python/api/azure-mgmt-containerinstance/)

