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

# Azure Load Balancer Operations Skill

## Overview

Azure Load Balancer provides **L4** (TCP/UDP) load balancing for VMs/internal services. Operational runbook: Pre-flight → Execute → Validate → Recover.

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
- Network VNet only → delegate to: `azure-vnet-ops`

## Variable Convention

Auth env quad (`AZURE_SUBSCRIPTION_ID` / `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET`) is a common skeleton — see [Credential Sources & Priority Order](../../azure-skill-generator/references/azure-cli-conventions.md#credential-sources-priority-order); never ask the user, fail if unset. Business placeholders:

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure Location (e.g., eastus) |
| `{{user.lb_name}}` | User input | Load Balancer name; ask once |
| `{{user.vm_name}}` / `{{user.nic_name}}` | User input | Target VM / NIC for backend pool |
| `{{output.lb_id}}` | Last API response | Parse: `.id` from Azure CLI output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

Pre-flight checks, retry/backoff (CLI fails → retry ≤3× → SDK fallback), and the Recover decision matrix (HALT vs retry for quota/throttling/5xx) are defined in [azure-cli-conventions.md](../../azure-skill-generator/references/azure-cli-conventions.md). LB types, SKU, and component tables are in [core-concepts.md](references/core-concepts.md).

## Operations

### Create Load Balancer
Primary CLI (public LB with probe + rule):
```bash
az network lb create --name "{{user.lb_name}}" --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" --public-ip-address "{{user.public_ip_name}}" \
  --frontend-ip-name "frontend-ip" --backend-pool-name "backend-pool" --output json
az network lb probe create --lb-name "{{user.lb_name}}" --resource-group "{{user.resource_group}}" \
  --name "health-probe" --protocol Tcp --port 80 --interval 15 --output json
az network lb rule create --lb-name "{{user.lb_name}}" --resource-group "{{user.resource_group}}" \
  --name "lb-rule" --protocol Tcp --frontend-port 80 --backend-port 80 \
  --frontend-ip-name "frontend-ip" --backend-pool-name "backend-pool" --probe-name "health-probe" --output json
```
Full command set + Azure SDK for Python fallback → [integration.md](references/integration.md). Validate: `az network lb show --name "{{user.lb_name}}" --resource-group "{{user.resource_group}}" --output json` (provisioningState = `Succeeded`).

### Add VM to Backend Pool
```bash
NIC_ID=$(az vm show --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" \
  --query "networkProfile.networkInterfaces[0].id" -o tsv)
az network nic ip-config address-pool add --address-pool "backend-pool" \
  --ip-config-name "ipconfig" --nic-name "{{user.nic_name}}" \
  --resource-group "{{user.resource_group}}" --lb-name "{{user.lb_name}}" --output json
```
Full command set → [integration.md](references/integration.md).

### Delete Load Balancer

**Safety Gate**: MUST obtain explicit user confirmation (user types exact LB name) before deletion — deleting the LB **cuts all traffic** routed through it.

```bash
az network lb show --name "{{user.lb_name}}" --resource-group "{{user.resource_group}}" --output json
# Confirm exact LB name with user, then:
az network lb delete --name "{{user.lb_name}}" --resource-group "{{user.resource_group}}" --output json
```
Full command set + SDK fallback → [integration.md](references/integration.md).

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
- DELETE LB (`az network lb delete`) → **required**; traffic impact (port list) warning + Safety=0 → ABORT
- DELETE rule (`az network lb rule delete`) → **required**; port-specific traffic disruption warning
- DELETE probe (`az network lb probe delete`) → **required**; check rule references first
- VM removal from backend pool → **required**; traffic disruption to that VM warned
- DELETE inbound NAT rule → **required**; port forwarding impact communicated
- CREATE LB / ADD VM to pool / LIST → recommended

## L4 Auto-Feedback Loop

For autonomous operation on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-loadbalancer-ops \
  --operation lb_create \
  --command "az network lb create --name {{user.lb_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"provisioningState": "Succeeded"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (create): auto-feedback loop active
- **Risky operations** (delete): always bypass loop and require explicit human confirmation
- Healing policy: see [`scripts/self_healing/loadbalancer_heal.json`](../../scripts/self_healing/loadbalancer_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md) — LB types, SKU, components
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md) — full CLI/SDK commands, credentials
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Load Balancer Docs](https://docs.microsoft.com/azure/load-balancer/)
- [Azure CLI Network Reference](https://docs.microsoft.com/cli/azure/network/lb)
- [Azure SDK Network Module](https://docs.microsoft.com/python/api/azure-mgmt-network/)
