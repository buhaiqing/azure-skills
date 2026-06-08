---
name: azure-vnet-ops
description: >-
  Use when operating Azure Virtual Network resources via Azure CLI or Azure SDK;
  user mentions "Virtual Network", "VNet", "subnet", address space, peering, or network segmentation.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints.
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

# Azure Virtual Network Operations Skill

## Overview

Azure Virtual Network (VNet) provides private network isolation, subnet segmentation, routing boundaries, and connectivity foundations for Azure workloads. Use this skill as the VNet/subnet operational runbook: **Pre-flight → Execute → Validate → Recover**.

## Trigger & Scope

### SHOULD Use When
- User mentions "Virtual Network", "VNet", "subnet", address space, CIDR, peering, or private network
- Task involves CRUD on **Virtual Networks** or **subnets**
- Task involves subnet delegation, service endpoints, DNS server settings, or address prefix changes
- Network foundation is required before VM, AKS, Application Gateway, Load Balancer, or private endpoint work

### SHOULD NOT Use When
- L4 load balancing → delegate to: `azure-loadbalancer-ops`
- L7 load balancing or WAF → delegate to: `azure-appgateway-ops`
- Global edge routing/CDN → delegate to: `azure-frontdoor-ops`
- DNS traffic routing → delegate to: `azure-trafficmanager-ops`
- VM lifecycle → delegate to: `azure-vm-ops`
- NSG-only changes → delegate to a future `azure-nsg-ops` or keep as dependency note

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure Location (e.g., eastus); validate |
| `{{user.vnet_name}}` | User input | VNet name; ask once |
| `{{user.address_prefixes}}` | User input | VNet CIDR list, e.g., 10.10.0.0/16 |
| `{{user.subnet_name}}` | User input | Subnet name; ask once for subnet operations |
| `{{user.subnet_prefix}}` | User input | Subnet CIDR, e.g., 10.10.1.0/24 |
| `{{output.vnet_id}}` | Last API response | Parse: `.id` from Azure CLI output |
| `{{output.subnet_id}}` | Last API response | Parse: `.id` from subnet output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**. Use Azure CLI first. If CLI fails after up to 3 retries with backoff, use Azure SDK for Python fallback. Poll LROs every 15 seconds for up to 20 minutes. See [Integration Setup](references/integration.md) for SDK client setup and RBAC.

### Operation: Create or Update Virtual Network

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show --output json` | HALT; configure env |
| Subscription valid | `az account list --output json` | HALT; select valid subscription |
| Resource Group exists | `az group show --name {{user.resource_group}} --output json` | Create or ask for existing Resource Group |
| Location valid | `az account list-locations --output json` | Ask for valid Azure Location |
| CIDR valid/non-overlap | Compare requested prefixes against existing VNets | HALT; request corrected address plan |

#### Execute
- CLI primary: `az network vnet create|update ... --output json`
- SDK fallback: `NetworkManagementClient.virtual_networks.begin_create_or_update(...)`
- Required fields: Resource Group, Location, VNet name, address prefixes, optional initial subnet

#### Validate
- Show VNet and confirm `provisioningState == Succeeded`
- Confirm address prefixes and subnet list match requested plan
- Capture full VNet resource ID in `{{output.vnet_id}}`

#### Recover
| Error | Action |
|-------|--------|
| AddressPrefixOverlap / InvalidAddressPrefix | HALT; ask for corrected CIDR |
| InUseSubnetCannotBeDeleted | HALT; identify dependent resources first |
| AuthorizationFailed | HALT; require Network Contributor or equivalent |
| Throttling (429) | Backoff, retry up to 3x |
| 5xx Internal | Retry up to 3x, then HALT |

### Operation: Manage Subnet

Use `az network vnet subnet create|update|show|list ... --output json` as CLI primary and `NetworkManagementClient.subnets.begin_create_or_update(...)` / `subnets.begin_delete(...)` as SDK fallback. Validate subnet prefix containment inside the parent VNet address space before mutation.

### Operation: Manage VNet Peering

Use `az network vnet peering create|update|delete|list ... --output json` as CLI primary and `NetworkManagementClient.virtual_network_peerings.begin_create_or_update(...)` / `begin_delete(...)` as SDK fallback. Validate both VNet resource IDs, non-overlapping address spaces, RBAC on both sides, and connectivity impact before mutation.

### Operation: Delete Subnet or Virtual Network

**Safety Gate**: MUST obtain explicit human confirmation before subnet or VNet deletion. Show dependent NICs, private endpoints, gateways, delegations, route tables, NSGs, and peering links first. User must type the exact subnet or VNet name.

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate. See `AGENTS.md §3–§8`.

| Parameter | Value |
|-----------|-------|
| GCL | **required** |
| max_iterations | 2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE VNet / subnet → **required**; dependency impact warning + Safety=0 → ABORT
- Address space or subnet prefix mutation → **required**; overlap and dependency check required
- Peering create/delete/update → **required**; cross-VNet connectivity impact warning
- CREATE VNet / subnet / LIST / SHOW → recommended

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Virtual Network Documentation](https://docs.microsoft.com/azure/virtual-network/)
- [Azure CLI VNet Reference](https://docs.microsoft.com/cli/azure/network/vnet)
- [Azure SDK Network Module](https://docs.microsoft.com/python/api/azure-mgmt-network/)
