---
name: azure-nsg-ops
description: >-
  Use when operating Azure Network Security Group (NSG) resources and security rules via Azure CLI or Azure SDK;
  user mentions "NSG", "Network Security Group", security rule, subnet association, NIC association, allow/deny traffic, or port filtering.
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

# Azure Network Security Group Operations Skill

## Overview

Azure Network Security Groups filter inbound and outbound traffic for subnets and network interfaces. Use this skill as the NSG operational runbook: **Pre-flight → Execute → Validate → Recover**.

## Trigger & Scope

### SHOULD Use When
- User mentions "NSG", "Network Security Group", security rules, allow/deny traffic, ports, protocols, or priorities
- Task involves CRUD on **Network Security Groups** or **security rules**
- Task involves associating or dissociating an NSG with a subnet or network interface
- Task requires validating effective security rules or diagnosing traffic blocked by NSG policy

### SHOULD NOT Use When
- VNet/subnet address space or peering changes → delegate to: `azure-vnet-ops`
- L4 load balancing → delegate to: `azure-loadbalancer-ops`
- L7 load balancing or WAF → delegate to: `azure-appgateway-ops`
- Private Endpoint lifecycle or Private Link approvals → delegate to: `azure-privateendpoint-ops`
- VM lifecycle → delegate to: `azure-vm-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure Location (e.g., eastus); validate |
| `{{user.nsg_name}}` | User input | NSG name; ask once |
| `{{user.rule_name}}` | User input | Security rule name; ask for rule operations |
| `{{user.subnet_id}}` | User input | Full subnet resource ID for subnet association |
| `{{user.nic_id}}` | User input | Full NIC resource ID for NIC association |
| `{{output.nsg_id}}` | Last API response | Parse: `.id` from NSG output |
| `{{output.rule_id}}` | Last API response | Parse: `.id` from security rule output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**. Use Azure CLI first. If CLI fails after up to 3 retries with backoff, use Azure SDK for Python fallback. Poll LROs every 15 seconds for up to 20 minutes. See [Integration Setup](references/integration.md) for SDK client setup and RBAC.

### Operation: Create or Update Network Security Group

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
<!-- 通用 5 步 Pre-flight 见 [azure-cli-conventions.md#pre-flight-checks-canonical-all-azure--ops-share](../../azure-skill-generator/references/azure-cli-conventions.md#pre-flight-checks-canonical-all-azure--ops-share) -->
| Name conflict | `az network nsg show --name {{user.nsg_name}} --resource-group {{user.resource_group}} --output json` | Treat as update if same target |

#### Execute
- CLI primary: `az network nsg create|update ... --output json`
- SDK fallback: `NetworkManagementClient.network_security_groups.begin_create_or_update(...)`
- Required fields: Resource Group, Location, NSG name, optional tags

#### Validate
- Show NSG and confirm `provisioningState == Succeeded`
- Capture full NSG resource ID in `{{output.nsg_id}}`
- Confirm expected tags and security rule list

#### Recover
| Error | Action |
|-------|--------|
| AuthorizationFailed | HALT; require Network Contributor or equivalent |
| LocationNotAvailableForResourceType | HALT; ask for valid Azure Location |
| ResourceGroupNotFound | HALT; ask for existing Resource Group |
| Throttling (429) | Backoff, retry up to 3x |
| 5xx Internal | Retry up to 3x, then HALT |

### Operation: Manage Security Rules

Use `az network nsg rule create|update|show|list|delete ... --output json` as CLI primary and `NetworkManagementClient.security_rules.begin_create_or_update(...)` / `begin_delete(...)` as SDK fallback. Validate unique priority, direction, access, protocol, source/destination prefixes, and port ranges before mutation.

### Operation: Associate NSG to Subnet or NIC

Use `az network vnet subnet update --network-security-group ... --output json` for subnet association and `az network nic update --network-security-group ... --output json` for NIC association. SDK fallback uses `NetworkManagementClient.subnets.begin_create_or_update(...)` or `network_interfaces.begin_create_or_update(...)` with the NSG reference. Validate full resource IDs and same subscription before mutation.

### Operation: Delete or Dissociate

Use `az network nsg delete`, `az network nsg rule delete`, `az network vnet subnet update --network-security-group ""`, and `az network nic update --network-security-group ""` as CLI primary. SDK fallback uses `network_security_groups.begin_delete(...)`, `security_rules.begin_delete(...)`, `subnets.begin_create_or_update(...)`, or `network_interfaces.begin_create_or_update(...)` after CLI retry exhaustion.

**Safety Gate**: MUST obtain explicit human confirmation before deleting an NSG, deleting a security rule, or dissociating an NSG from a subnet/NIC. Show impacted subnet/NIC IDs, effective rules, and expected traffic impact first. User must type the exact NSG or rule name for delete, or the exact subnet/NIC resource ID for dissociation.

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate. See `AGENTS.md §3–§8`.

| Parameter | Value |
|-----------|-------|
| GCL | **required** |
| max_iterations | 2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE NSG / security rule → **required**; traffic impact warning + Safety=0 → ABORT
- Dissociate NSG from subnet/NIC → **required**; exposure impact warning + Safety=0 → ABORT
- Security rule create/update → **required**; priority conflict and reachability check required
- LIST / SHOW / effective rule inspection → recommended

## L4 Auto-Feedback Loop

For autonomous operation on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-nsg-ops \
  --operation nsg_create \
  --command "az network nsg create --name {{user.nsg_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"provisioningState": "Succeeded"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (nsg_create, nsg_rule_create): auto-feedback loop active
- **Risky operations** (delete NSG/rule, dissociate NSG from subnet/NIC): always bypass loop and require explicit human confirmation
- Healing policy: see [`scripts/self_healing/nsg_heal.json`](../../scripts/self_healing/nsg_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Network Security Groups Documentation](https://docs.microsoft.com/azure/virtual-network/network-security-groups-overview)
- [Azure CLI NSG Reference](https://docs.microsoft.com/cli/azure/network/nsg)
- [Azure SDK Network Module](https://docs.microsoft.com/python/api/azure-mgmt-network/)

