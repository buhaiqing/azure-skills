---
name: azure-loadbalancer-ops
description: >-
  Use when operating Azure Load Balancer resources via Azure CLI or Azure SDK;
  user mentions "Load Balancer", "ALB", "LB", "Azure Load Balancer", or L4 load balancing.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-05-10"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Load Balancer Operations Skill

## Overview

Azure Load Balancer provides **Layer 4 (L4)** load balancing for VMs and internal services. This skill is an operational runbook with explicit scope, credential rules, pre-flight checks, dual-path execution (Azure CLI + Azure SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure Load Balancer", "ALB", "LB", or "Load Balancer"
- Task involves CRUD on **Load Balancer** resources (create, show, update, delete, list)
- Keywords: load balancer, backend pool, frontend IP, health probe, load balancing rule, inbound NAT rule, outbound rule
- L4 load balancing requirements (TCP/UDP)

### SHOULD NOT Use When
- L7 (HTTP/HTTPS) load balancing → delegate to: `azure-appgateway-ops`
- Global/multi-region load balancing → delegate to: `azure-frontdoor-ops`
- DNS-based routing → delegate to: `azure-trafficmanager-ops`
- Billing only → delegate to: `azure-cost-ops`
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
| `{{user.lb_name}}` | User input | Load Balancer name; ask once |
| `{{output.lb_id}}` | Last API response | Parse: `.id` from Azure CLI output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create Load Balancer

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show` | HALT; configure env |
| Subscription valid | `az account list --output json` | Suggest valid subscription |
| Resource Group exists | `az group show --name {{user.resource_group}}` | Create or suggest existing |
| Location valid | `az account list-locations --output json` | Suggest valid location |
| VNet exists (if internal LB) | `az network vnet show --name {{vnet}} --resource-group {{rg}}` | HALT; create VNet first |
| Public IP exists (if public LB) | `az network public-ip show --name {{pip}} --resource-group {{rg}}` | HALT; create Public IP first |

#### Execute — Azure CLI (Primary)
```bash
# Create Public Load Balancer
az network lb create \
  --name "{{user.lb_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --public-ip-address "{{user.public_ip_name}}" \
  --frontend-ip-name "frontend-ip" \
  --backend-pool-name "backend-pool" \
  --output json

# Create Health Probe
az network lb probe create \
  --lb-name "{{user.lb_name}}" \
  --resource-group "{{user.resource_group}}" \
  --name "health-probe" \
  --protocol Tcp \
  --port 80 \
  --interval 15 \
  --output json

# Create Load Balancing Rule
az network lb rule create \
  --lb-name "{{user.lb_name}}" \
  --resource-group "{{user.resource_group}}" \
  --name "lb-rule" \
  --protocol Tcp \
  --frontend-port 80 \
  --backend-port 80 \
  --frontend-ip-name "frontend-ip" \
  --backend-pool-name "backend-pool" \
  --probe-name "health-probe" \
  --output json
```

#### Execute — Azure SDK (Fallback)
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient
import os

credential = DefaultAzureCredential()
client = NetworkManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

# Create Load Balancer
lb = client.load_balancers.begin_create_or_update(
    resource_group_name='{{user.resource_group}}',
    load_balancer_name='{{user.lb_name}}',
    parameters={
        'location': '{{user.location}}',
        'frontend_ip_configurations': [{
            'name': 'frontend-ip',
            'public_ip_address': {'id': '{{user.public_ip_id}}'}
        }],
        'backend_address_pools': [{'name': 'backend-pool'}],
        'probes': [{
            'name': 'health-probe',
            'protocol': 'Tcp',
            'port': 80,
            'interval_in_seconds': 15
        }],
        'load_balancing_rules': [{
            'name': 'lb-rule',
            'protocol': 'Tcp',
            'frontend_port': 80,
            'backend_port': 80,
            'frontend_ip_configuration': {'id': 'frontend-ip-id'},
            'backend_address_pool': {'id': 'backend-pool-id'},
            'probe': {'id': 'probe-id'}
        }]
    }
).result()
```

#### Validate
```bash
# Verify Load Balancer state
az network lb show --name "{{user.lb_name}}" --resource-group "{{user.resource_group}}" --output json

# Check provisioning state: should be "Succeeded"
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| QuotaExceeded | HALT; request quota increase |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |
| Public IP not found | HALT; create Public IP first |
| VNet not found | HALT; create VNet first |

### Operation: Add VM to Backend Pool

```bash
# Get VM NIC ID
NIC_ID=$(az vm show --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --query "networkProfile.networkInterfaces[0].id" -o tsv)

# Add NIC to backend pool
az network nic ip-config address-pool add \
  --address-pool "backend-pool" \
  --ip-config-name "ipconfig" \
  --nic-name "{{user.nic_name}}" \
  --resource-group "{{user.resource_group}}" \
  --lb-name "{{user.lb_name}}" \
  --output json
```

### Operation: Delete Load Balancer

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

```bash
# Show Load Balancer before deletion
az network lb show --name "{{user.lb_name}}" --resource-group "{{user.resource_group}}" --output json

# Request confirmation - user must type exact LB name
# Then proceed with deletion:
az network lb delete --name "{{user.lb_name}}" --resource-group "{{user.resource_group}}" --output json
```

## Load Balancer Types

| Type | SKU | Use Case |
|------|-----|----------|
| **Public** | Basic/Standard | Internet-facing, inbound traffic |
| **Internal** | Basic/Standard | Internal services, VNet-only |
| **Basic** | Basic | Dev/test, limited HA |
| **Standard** | Standard | Production, zone-redundant, HA ports |

## Key Components

| Component | Purpose | CLI Command |
|-----------|---------|-------------|
| **Frontend IP** | Entry point for traffic | `az network lb frontend-ip create` |
| **Backend Pool** | Target VMs/NICs | `az network lb address-pool create` |
| **Health Probe** | Health check | `az network lb probe create` |
| **Load Balancing Rule** | Traffic distribution | `az network lb rule create` |
| **Inbound NAT Rule** | Port forwarding | `az network lb inbound-nat-rule create` |
| **Outbound Rule** | Outbound SNAT | `az network lb outbound-rule create` |

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)

## See Also

- [Azure Load Balancer Docs](https://docs.microsoft.com/azure/load-balancer/)
- [Azure CLI Network Reference](https://docs.microsoft.com/cli/azure/network/lb)
- [Azure SDK Network Module](https://docs.microsoft.com/python/api/azure-mgmt-network/)