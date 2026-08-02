---
name: azure-aks-ops
description: >-
  Use when operating Azure Kubernetes Service (AKS) resources via Azure CLI or Azure SDK;
  user mentions "AKS", "Azure Kubernetes Service", "Kubernetes", "K8s", or container orchestration.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), kubectl, valid Azure credentials (Service Principal),
  network access to Azure endpoints and AKS clusters.
metadata:
  author: azure
  version: "1.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Kubernetes Service (AKS) Operations Skill

## Overview

Azure Kubernetes Service (AKS) is Azure's managed Kubernetes service for deploying, managing, and scaling containerized applications. This skill is an operational runbook: explicit scope, credential rules, dual-path execution (Azure CLI + Azure SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure Kubernetes Service", "AKS", "Kubernetes", "K8s"
- Task involves CRUD on **AKS clusters** (create, show, update, delete, list)
- Keywords: aks, kubernetes, cluster, node pool, pod, deployment, container, helm, kubectl
- Managed Kubernetes requirements / container orchestration operations

### SHOULD NOT Use When (delegate)
- Container Instances only → `azure-aci-ops`
- Container Registry only → `azure-acr-ops`
- Billing only → `azure-cost-ops`
- RBAC/IAM only → `azure-rbac-ops`
- Network VNet only → `azure-vnet-ops`

## Variable Convention

Auth env quad (`AZURE_SUBSCRIPTION_ID` / `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET`) is a common skeleton — see [Credential Sources & Priority Order](../../azure-skill-generator/references/azure-cli-conventions.md#credential-sources-priority-order). Business placeholders used in this skill:

- `{{user.resource_group}}` — Resource Group (ask once; reuse)
- `{{user.location}}` — Location (e.g., eastus)
- `{{user.aks_name}}` — AKS cluster name (ask once)
- `{{user.node_count}}` / `{{user.new_node_count}}` — node count (default 3)
- `{{user.node_vm_size}}` — VM size (default Standard_DS2_v2)
- `{{user.nodepool_name}}` — node pool name
- `{{user.target_version}}` — target Kubernetes version
- `{{output.aks_id}}` — parse `.id` from CLI output
- `{{output.kube_config}}` — parse `.kubeConfig` or fetch via `az aks get-credentials`

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

Pre-flight checks (CLI/credential/subscription/RG/location/quota/kubectl) and the 3× retry-then-SDK fallback are defined in [azure-cli-conventions.md](../../azure-skill-generator/references/azure-cli-conventions.md). Full `az aks ...` command blocks + Azure SDK for Python snippets live in [integration.md](references/integration.md).

## Operations

### Create Cluster
```bash
az aks create --name "{{user.aks_name}}" --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" --node-count "{{user.node_count}}" \
  --node-vm-size "{{user.node_vm_size}}" --generate-ssh-keys \
  --enable-managed-identity --output json
az aks get-credentials --name "{{user.aks_name}}" --resource-group "{{user.resource_group}}" --output json
```
Full commands (multi-node-pool, advanced networking, monitoring addon) + SDK fallback: [integration.md](references/integration.md).

### Add / Scale Node Pool
```bash
az aks nodepool add --cluster-name "{{user.aks_name}}" --resource-group "{{user.resource_group}}" \
  --name "{{user.nodepool_name}}" --node-count "{{user.node_count}}" --node-vm-size "{{user.node_vm_size}}" --output json
az aks nodepool scale --cluster-name "{{user.aks_name}}" --resource-group "{{user.resource_group}}" \
  --name "{{user.nodepool_name}}" --node-count "{{user.new_node_count}}" --output json
```
Scale default pool: `az aks scale ... --node-count "{{user.new_node_count}}"`. Full + SDK: [integration.md](references/integration.md).

### Upgrade Cluster
```bash
az aks get-upgrades --name "{{user.aks_name}}" --resource-group "{{user.resource_group}}" --output json
az aks upgrade --name "{{user.aks_name}}" --resource-group "{{user.resource_group}}" \
  --kubernetes-version "{{user.target_version}}" --output json
```
Full + SDK + rollback strategy: [integration.md](references/integration.md).

### List / Show Clusters
```bash
az aks list --output json
az aks list --resource-group "{{user.resource_group}}" --output json
az aks show --name "{{user.aks_name}}" --resource-group "{{user.resource_group}}" --output json
```

### Get Credentials (kubectl)
```bash
az aks get-credentials --name "{{user.aks_name}}" --resource-group "{{user.resource_group}}" --output json
```
Verify with `kubectl get nodes`. kubectl cheat sheet: [core-concepts.md](references/core-concepts.md#kubectl-cheat-sheet).

### Delete Cluster — ⚠️ Safety Gate
**MUST obtain explicit user confirmation (type exact cluster name) before deletion.**
```bash
az aks show --name "{{user.aks_name}}" --resource-group "{{user.resource_group}}" --output json
az aks delete --name "{{user.aks_name}}" --resource-group "{{user.resource_group}}" --yes --output json
```

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate. See `AGENTS.md §3–§8` for the spec.

Risk tiers: R0 read / R1 mutable / R2 destructive — see [`scripts/risk_tiers.json`](../scripts/risk_tiers.json); enforced by auto_feedback_loop.

| Parameter | Value |
|-----------|-------|
| GCL | **required** |
| max_iterations | 2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE cluster (`az aks delete`) → **required**; Safety=0 → ABORT
- STOP cluster (`az aks stop`) → **required**; workload downtime warning + Safety=0 → ABORT
- SCALE node pool to 0 → **required**; pod eviction warning + Safety=0 → ABORT
- NODEPOOL DELETE → **required**; pod disruption warning + Safety=0 → ABORT
- UPGRADE cluster → **required**; pre-check (`az aks get-upgrades`) + rollback strategy
- CREATE / SCALE (non-zero) → recommended

## L4 Auto-Feedback Loop

For autonomous operation without a human gate on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-aks-ops \
  --operation aks_create \
  --command "az aks create --name {{user.aks_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"provisioningState": "Succeeded"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (create, scale): auto-feedback loop active — observes cluster provisioningState, diffs against desired, self-heals via `az aks wait`
- **Risky operations** (delete, stop, scale-to-zero): always bypass the loop and require explicit human confirmation — safety gate cannot be overridden
- Healing policy: see [`scripts/self_healing/aks_heal.json`](../../scripts/self_healing/aks_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md) — architecture, node pools, networking models, identity, kubectl cheat sheet
- [Troubleshooting](references/troubleshooting.md) — cluster/node pool issues, upgrade failures
- [Integration Setup](references/integration.md) — full `az aks ...` commands + Azure SDK fallback, ACR/VNet/monitoring
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)



> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
