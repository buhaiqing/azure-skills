---
name: azure-privateendpoint-ops
description: >-
  Use when operating Azure Private Endpoint and Private Link connection resources via Azure CLI or Azure SDK;
  user mentions "Private Endpoint", "Private Link", private DNS zone group, private connection approval, or private service connectivity.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure Resource Manager endpoints.
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

# Azure Private Endpoint Operations Skill

## Overview

Azure Private Endpoint provides private IP connectivity from a Virtual Network to Azure services through Private Link. Use this skill as the Private Endpoint operational runbook: **Pre-flight → Execute → Validate → Recover**.

## Trigger & Scope

### SHOULD Use When
- User mentions "Private Endpoint", "Private Link", private DNS zone group, private connection approval, or private service access
- Task involves CRUD on **Private Endpoints**
- Task involves approving, rejecting, or inspecting Private Link service connections
- Task involves associating a Private Endpoint with private DNS zone groups
- Task requires validating private IP allocation or connection state

### SHOULD NOT Use When
- VNet/subnet creation, address space, peering, or subnet delegation → delegate to: `azure-vnet-ops`
- NSG or security rule changes → delegate to: `azure-nsg-ops`
- Load balancer, Application Gateway, Front Door, or Traffic Manager operations → delegate to their respective skills
- Target service lifecycle (Storage, Key Vault, App Service, AKS, VM) → delegate to that service skill

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure Location (e.g., eastus); validate |
| `{{user.private_endpoint_name}}` | User input | Private Endpoint name; ask once |
| `{{user.subnet_id}}` | User input | Full subnet resource ID |
| `{{user.private_link_resource_id}}` | User input | Full target service resource ID |
| `{{user.group_id}}` | User input | Target subresource group ID, e.g., blob, vault, sites |
| `{{user.connection_name}}` | User input | Private Link service connection name |
| `{{user.private_dns_zone_id}}` | User input | Full private DNS zone resource ID |
| `{{output.private_endpoint_id}}` | Last API response | Parse: `.id` from Private Endpoint output |
| `{{output.connection_state}}` | Last API response | Parse connection status |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**. Use Azure CLI first. If CLI fails after up to 3 retries with backoff, use Azure SDK for Python fallback. Poll LROs every 15 seconds for up to 30 minutes. See [Integration Setup](references/integration.md) for SDK client setup and RBAC.

### Operation: Create or Update Private Endpoint

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show --output json` | HALT; configure env |
| Subscription valid | `az account show --subscription {{env.AZURE_SUBSCRIPTION_ID}} --output json` | HALT; select valid subscription |
| Resource Group exists | `az group show --name {{user.resource_group}} --output json` | Create or ask for existing Resource Group |
| Location valid | `az account list-locations --output json` | Ask for valid Azure Location |
| Subnet exists | `az network vnet subnet show --ids {{user.subnet_id}} --output json` | HALT; delegate subnet work to `azure-vnet-ops` |
| Target resource exists | `az resource show --ids {{user.private_link_resource_id}} --output json` | HALT; delegate target lifecycle to service skill |
| Group ID valid | Compare with target Private Link resource metadata | Ask for valid subresource group ID |

#### Execute
- CLI primary: `az network private-endpoint create|update ... --output json`
- SDK fallback: `NetworkManagementClient.private_endpoints.begin_create_or_update(...)`
- Required fields: Resource Group, Location, Private Endpoint name, subnet ID, target resource ID, group ID, connection name

#### Validate
- Show Private Endpoint and confirm `provisioningState == Succeeded`
- Confirm connection state is `Approved` or document `Pending` approval owner
- Confirm private IP allocation and NIC reference
- Capture full Private Endpoint resource ID in `{{output.private_endpoint_id}}`

#### Recover
| Error | Action |
|-------|--------|
| PrivateEndpointCannotBeCreatedInSubnetThatHasNetworkPoliciesEnabled | HALT; request subnet policy change through `azure-vnet-ops` |
| InvalidPrivateLinkServiceId | HALT; ask for full target resource ID |
| GroupIdInvalid | HALT; ask for valid group ID |
| AuthorizationFailed | HALT; require Network Contributor and target-service approval rights |
| Throttling (429) | Backoff, retry up to 3x |
| 5xx Internal | Retry up to 3x, then HALT |

### Operation: Manage Private DNS Zone Group

Use `az network private-endpoint dns-zone-group create|update|show|list|delete ... --output json` as CLI primary and `NetworkManagementClient.private_dns_zone_groups.begin_create_or_update(...)` / `begin_delete(...)` as SDK fallback. Validate full private DNS zone resource ID and expected zone name before mutation.

### Operation: Approve or Reject Private Link Connection

Use the target service's private endpoint connection command when available; otherwise use `az network private-endpoint-connection approve|reject|show|list ... --output json` where supported. SDK fallback uses the target service management client when the approval API is service-specific; do not guess unsupported methods.

### Operation: Delete Private Endpoint or DNS Zone Group

Use `az network private-endpoint delete` and `az network private-endpoint dns-zone-group delete` as CLI primary. SDK fallback uses `private_endpoints.begin_delete(...)` or `private_dns_zone_groups.begin_delete(...)` after CLI retry exhaustion. Connection rejection uses verified target-service CLI or SDK approval APIs only.

**Safety Gate**: MUST obtain explicit human confirmation before deleting a Private Endpoint, deleting a DNS zone group, rejecting a connection, or removing DNS integration. Show target resource ID, subnet ID, private IP, connection state, DNS zone IDs, and expected connectivity impact first. User must type the exact Private Endpoint name, DNS zone group name, or connection name.

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate. See `AGENTS.md §3–§8`.

| Parameter | Value |
|-----------|-------|
| GCL | **required** |
| max_iterations | 2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE Private Endpoint / DNS zone group → **required**; connectivity impact warning + Safety=0 → ABORT
- Reject Private Link connection → **required**; target service impact warning + Safety=0 → ABORT
- Create/update Private Endpoint → **required**; subnet, target resource, group ID, and DNS validation required
- LIST / SHOW / connection state inspection → recommended

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Private Endpoint Documentation](https://docs.microsoft.com/azure/private-link/private-endpoint-overview)
- [Azure CLI Private Endpoint Reference](https://docs.microsoft.com/cli/azure/network/private-endpoint)
- [Azure SDK Network Module](https://docs.microsoft.com/python/api/azure-mgmt-network/)

