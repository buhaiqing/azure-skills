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

Azure Kubernetes Service (AKS) is Azure's managed Kubernetes service for deploying, managing, and scaling containerized applications. This skill is an operational runbook with explicit scope, credential rules, pre-flight checks, dual-path execution (Azure CLI + Azure SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure Kubernetes Service", "AKS", "Kubernetes", "K8s"
- Task involves CRUD on **AKS clusters** (create, show, update, delete, list)
- Keywords: aks, kubernetes, cluster, node pool, pod, deployment, container, helm, kubectl
- Managed Kubernetes requirements
- Container orchestration operations

### SHOULD NOT Use When
- Container Instances only → delegate to: `azure-containerinstance-ops`
- Container Registry only → delegate to: `azure-acr-ops`
- Billing only → delegate to: `azure-cost-ops`
- RBAC/IAM only → delegate to: `azure-rbac-ops`
- Network VNet only → delegate to: `azure-network-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure region (e.g., eastus) |
| `{{user.aks_name}}` | User input | AKS cluster name; ask once |
| `{{user.node_count}}` | User input | Number of nodes (default: 3) |
| `{{user.node_vm_size}}` | User input | VM size for nodes (default: Standard_DS2_v2) |
| `{{output.aks_id}}` | Last API response | Parse: `.id` from Azure CLI output |
| `{{output.kube_config}}` | Last API response | Parse: `.kubeConfig` or fetch via `az aks get-credentials` |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create AKS Cluster

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show` | HALT; configure env |
| Subscription valid | `az account list --output json` | Suggest valid subscription |
| Resource Group exists | `az group show --name {{user.resource_group}}` | Create or suggest existing |
| Location valid | `az account list-locations --output json` | Suggest valid location |
| Quota check | `az vm list-skus --location {{location}}` | HALT; request quota increase |
| kubectl available | `kubectl version --client` | Install kubectl |

#### Execute — Azure CLI (Primary)
```bash
# Create AKS cluster with default node pool
az aks create \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --node-count "{{user.node_count}}" \
  --node-vm-size "{{user.node_vm_size}}" \
  --generate-ssh-keys \
  --enable-managed-identity \
  --output json

# Get cluster credentials for kubectl
az aks get-credentials \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

#### Execute — Azure CLI (Advanced Options)
```bash
# Create AKS with multiple node pools
az aks create \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --node-count 3 \
  --node-vm-size "Standard_DS2_v2" \
  --nodepool-name "systempool" \
  --generate-ssh-keys \
  --enable-managed-identity \
  --network-plugin azure \
  --network-policy calico \
  --enable-addons monitoring \
  --output json

# Add additional node pool
az aks nodepool add \
  --cluster-name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --name "userpool" \
  --node-count 5 \
  --node-vm-size "Standard_DS3_v2" \
  --output json
```

#### Execute — Azure SDK (Fallback)
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerservice import ContainerServiceClient
import os

credential = DefaultAzureCredential()
client = ContainerServiceClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

# Create AKS cluster
cluster = client.managed_clusters.begin_create_or_update(
    resource_group_name='{{user.resource_group}}',
    resource_name='{{user.aks_name}}',
    parameters={
        'location': '{{user.location}}',
        'identity': {'type': 'SystemAssigned'},
        'agent_pool_profiles': [{
            'name': 'agentpool',
            'count': {{user.node_count}},
            'vm_size': '{{user.node_vm_size}}',
            'mode': 'System',
            'os_type': 'Linux'
        }],
        'dns_prefix': '{{user.aks_name}}',
        'network_profile': {
            'network_plugin': 'azure',
            'network_policy': 'calico'
        }
    }
).result()
```

#### Validate
```bash
# Verify AKS cluster state
az aks show --name "{{user.aks_name}}" --resource-group "{{user.resource_group}}" --output json

# Check provisioning state: should be "Succeeded"
# Verify node status via kubectl
kubectl get nodes
kubectl get pods -A
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| QuotaExceeded | HALT; request quota increase |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |
| VMSizeNotAvailable | Suggest alternative VM size |
| NetworkProfileConflict | Check VNet/subnet config |

### Operation: Scale Node Pool

```bash
# Scale node count in default node pool
az aks scale \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --node-count "{{user.new_node_count}}" \
  --output json

# Scale specific node pool
az aks nodepool scale \
  --cluster-name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --name "{{user.nodepool_name}}" \
  --node-count "{{user.new_node_count}}" \
  --output json
```

### Operation: Upgrade Cluster

```bash
# Check available upgrades
az aks get-upgrades \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Upgrade Kubernetes version
az aks upgrade \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --kubernetes-version "{{user.target_version}}" \
  --output json
```

### Operation: List AKS Clusters

```bash
# List all AKS clusters in subscription
az aks list --output json

# List AKS clusters in specific resource group
az aks list --resource-group "{{user.resource_group}}" --output json
```

### Operation: Delete AKS Cluster

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

```bash
# Show AKS cluster before deletion
az aks show --name "{{user.aks_name}}" --resource-group "{{user.resource_group}}" --output json

# Request confirmation - user must type exact cluster name
# Then proceed with deletion:
az aks delete --name "{{user.aks_name}}" --resource-group "{{user.resource_group}}" --yes --output json
```

## AKS Cluster Configuration

### Network Models
| Model | Description | Use Case |
|-------|-------------|----------|
| **kubenet** | Basic networking, VNet not required | Simple dev/test |
| **azure** | Advanced CNI, VNet integration | Production, VNet integration |

### Identity Models
| Model | Description | Recommendation |
|-------|-------------|----------------|
| **SystemAssigned** | Managed identity created with cluster | Recommended |
| **UserAssigned** | Pre-existing managed identity | Advanced scenarios |

### Node Pool Modes
| Mode | Purpose | Constraints |
|------|---------|-------------|
| **System** | Runs critical system pods | At least 1 required |
| **User** | Runs user workloads | Can have multiple |

## Key Components

| Component | Purpose | CLI Command |
|-----------|---------|-------------|
| **Managed Cluster** | AKS cluster resource | `az aks create/show/delete` |
| **Node Pool** | Group of nodes with same config | `az aks nodepool add/scale/delete` |
| **kubeconfig** | Cluster access credentials | `az aks get-credentials` |
| **Addons** | Monitoring, HTTP app routing | `az aks enable-addons` |
| **Network Profile** | CNI, network policy | Specified at creation |
| **Upgrade** | Kubernetes version update | `az aks upgrade` |

## kubectl Integration

After cluster creation, use kubectl for Kubernetes operations:

```bash
# Get credentials (merges into ~/.kube/config)
az aks get-credentials --name "{{user.aks_name}}" --resource-group "{{user.resource_group}}"

# Verify cluster access
kubectl cluster-info
kubectl get nodes
kubectl get namespaces

# Deploy application
kubectl create deployment nginx --image=nginx
kubectl scale deployment nginx --replicas=3
kubectl expose deployment nginx --port=80 --type=LoadBalancer
```

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate.
See `AGENTS.md §3–§8` for the spec.

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

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure AKS Documentation](https://docs.microsoft.com/azure/aks/)
- [Azure CLI AKS Reference](https://docs.microsoft.com/cli/azure/aks)
- [Azure SDK ContainerService Module](https://docs.microsoft.com/python/api/azure-mgmt-containerservice/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
