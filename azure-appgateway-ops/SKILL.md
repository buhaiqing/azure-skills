---
name: azure-appgateway-ops
description: >-
  Use when operating Azure Application Gateway resources via Azure CLI or Azure SDK;
  user mentions "Application Gateway", "App Gateway", "AGW", "WAF", or L7 load balancing.
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

# Azure Application Gateway Operations Skill

## Overview

Azure Application Gateway provides **Layer 7 (L7)** application-level load balancing with SSL termination, URL-based routing, and Web Application Firewall (WAF). This skill is an operational runbook: scope, credential rules, dual-path execution (Azure CLI + Azure SDK), validation, and recovery. Full commands and tables live in `references/`.

## Trigger & Scope

### SHOULD Use When
- User mentions "Application Gateway", "App Gateway", "AGW", "WAF"
- Task involves CRUD on **Application Gateway** resources
- Keywords: application gateway, backend pool, listener, rule, ssl certificate, waf, url routing
- L7 load balancing (HTTP/HTTPS), SSL termination, URL path routing, cookie session affinity, WAF protection

### SHOULD NOT Use When (delegate)
- L4 (TCP/UDP) load balancing → `azure-loadbalancer-ops`
- Global/multi-region load balancing → `azure-frontdoor-ops`
- DNS-based routing → `azure-trafficmanager-ops`
- Billing only → `azure-cost-ops`
- VNet/Subnet only → `azure-network-ops`

## Variable Convention

Auth env quad (`AZURE_SUBSCRIPTION_ID` / `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET`) is a common skeleton — see [Credential Sources & Priority Order](../../azure-skill-generator/references/azure-cli-conventions.md#credential-sources-priority-order); never ask the user, fail if unset. Business placeholders: `{{user.resource_group}}`, `{{user.location}}`, `{{user.agw_name}}`, `{{user.public_ip_name}}`, `{{user.vnet_name}}`, `{{user.subnet_name}}`, `{{user.backend_server_addresses}}`, `{{user.ssl_cert_path}}`, `{{user.ssl_cert_password}}`, `{{user.waf_policy_name}}`, `{{user.waf_policy_id}}` (ask once, reuse); `{{output.agw_id}}` parsed from last API response (`.id`).

## Execution Flow Pattern

Every operation: **Pre-flight → Execute → Validate → Recover**.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

Pre-flight checks (CLI/credentials/subscription/RG/location/VNet/dedicated subnet/Public IP) and the 3× retry-then-SDK fallback follow [azure-cli-conventions.md](../../azure-skill-generator/references/azure-cli-conventions.md). Full `az` command blocks and the Recover decision table are in [integration.md](references/integration.md).

## Operations

### Create Application Gateway
Primary CLI (basic; add `--cert-file`/`--cert-password` for SSL, or `--sku WAF_v2` for WAF):
```bash
az network application-gateway create --name "{{user.agw_name}}" --resource-group "{{user.resource_group}}" --location "{{user.location}}" --capacity 2 --sku Standard_v2 --public-ip-address "{{user.public_ip_name}}" --vnet-name "{{user.vnet_name}}" --subnet "{{user.subnet_name}}" --servers "{{user.backend_server_addresses}}" --output json
```
Full variants + Azure SDK fallback: [integration.md](references/integration.md).

### Add Backend Pool
```bash
az network application-gateway address-pool create --gateway-name "{{user.agw_name}}" --resource-group "{{user.resource_group}}" --name "backend-pool-2" --servers "{{user.backend_server_addresses}}" --output json
```
Full command: [integration.md](references/integration.md).

### Configure URL Path Routing
```bash
az network application-gateway url-path-map create --gateway-name "{{user.agw_name}}" --resource-group "{{user.resource_group}}" --name "url-path-map" --path-rules "/images/*=backend-pool-images /api/*=backend-pool-api" --default-address-pool "backend-pool-default" --output json
```
Full command: [integration.md](references/integration.md).

### Enable WAF Policy
```bash
az network application-gateway waf-policy create --name "{{user.waf_policy_name}}" --resource-group "{{user.resource_group}}" --type OWASP --version 3.0 --output json
```
Associate via `az network application-gateway update --set wafConfiguration.enabled=true --waf-policy "{{user.waf_policy_id}}"`. Full commands: [integration.md](references/integration.md).

### Delete Application Gateway

**Safety Gate**: MUST obtain explicit user confirmation (user must type the exact AGW name) before deletion — deleting cuts all traffic.

```bash
az network application-gateway show --name "{{user.agw_name}}" --resource-group "{{user.resource_group}}" --output json
# After explicit confirmation:
az network application-gateway delete --name "{{user.agw_name}}" --resource-group "{{user.resource_group}}" --output json
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
- DELETE gateway (`az network application-gateway delete`) → **required**; traffic impact warning + Safety=0 → ABORT
- BACKEND POOL REMOVE (referenced by rule) → **required**; traffic disruption warning + Safety=0 → ABORT
- WAF POLICY enable/create → **required**; Detection vs Prevention mode confirmed
- SSL CERTIFICATE upload → **required**; password handled securely — NEVER in trace
- URL PATH MAP / LISTENER / RULE changes affecting active traffic → **required**; disruption warning
- CREATE gateway / LIST / SHOW → recommended

### SSL Certificate Password Security

SSL certificate passwords are sensitive credentials. The GCL trace MUST NOT contain the `--cert-password` value. The Critic scans for password strings in command args and output. If detected, safety=0 → ABORT, regardless of operation success.

## L4 Auto-Feedback Loop

For autonomous operation on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-appgateway-ops \
  --operation appgateway_create \
  --command "az network application-gateway create --name {{user.gateway_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"provisioningState": "Succeeded"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (create, update): auto-feedback loop active
- **Risky operations** (delete): always bypass loop and require explicit human confirmation
- Healing policy: see [`scripts/self_healing/appgateway_heal.json`](../../scripts/self_healing/appgateway_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md) — AGW components, SKU, architecture, limits
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md) — full `az` command blocks, SDK fallback, Recover table
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Application Gateway Docs](https://docs.microsoft.com/azure/application-gateway/)
- [Azure CLI App Gateway Reference](https://docs.microsoft.com/cli/azure/network/application-gateway)
- [WAF Configuration](https://docs.microsoft.com/azure/web-application-firewall/ag/ag-overview)

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
