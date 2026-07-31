---
name: azure-frontdoor-ops
description: >-
  Use when operating Azure Front Door resources via Azure CLI or Azure SDK;
  user mentions "Front Door", "FD", "Front Door Standard", "Front Door Premium", 
  or global/multi-region load balancing.
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

# Azure Front Door Operations Skill

## Overview

Azure Front Door provides **global Layer 7** load balancing with CDN acceleration, multi-region routing, and Web Application Firewall (WAF). This skill is an operational runbook: scope, credential rules, dual-path execution (Azure CLI + Azure SDK), validation, and recovery. Full commands and tables live in `references/`.

## Trigger & Scope

### SHOULD Use When
- User mentions "Front Door", "FD", "Front Door Standard", "Front Door Premium"
- Task involves CRUD on **Front Door** resources
- Keywords: front door, frontend, backend pool, routing rule, health probe, origin group, endpoint, rule set
- Global/multi-region load balancing, CDN acceleration, WAF at global edge

### SHOULD NOT Use When
- L4 (TCP/UDP) load balancing → delegate to: `azure-loadbalancer-ops`
- Single-region L7 load balancing → delegate to: `azure-appgateway-ops`
- DNS-based routing only → delegate to: `azure-trafficmanager-ops`
- Billing only → delegate to: `azure-cost-ops`

## Variable Convention

Auth env quad (`{{env.AZURE_SUBSCRIPTION_ID/TENANT_ID/CLIENT_ID/SECRET}}`) is a common skeleton — see [Credential Sources & Priority Order](../../azure-skill-generator/references/azure-cli-conventions.md#credential-sources-priority-order); never ask the user, fail if unset. Business placeholders:

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.fd_name}}` | User input | Front Door profile name; ask once |
| `{{user.endpoint_name}}` | User input | Front Door endpoint name; ask once |
| `{{user.backend_host}}` | User input | Origin backend hostname |
| `{{user.custom_domain}}` | User input | Custom domain hostname |
| `{{output.fd_id}}` | Last API response | Parse: `.id` from Azure CLI output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

Pre-flight checks (CLI/credentials/subscription/RG/name uniqueness) and the 3× retry then SDK fallback follow [azure-cli-conventions.md](../../azure-skill-generator/references/azure-cli-conventions.md). Full `az afd` command blocks + SDK fallback + Recover table are in [integration.md](references/integration.md). SKU/components/FD-vs-AGW comparison tables are in [core-concepts.md](references/core-concepts.md).

## Operations

### Create Front Door Profile (profile + endpoint + origin-group + origin + route)
```bash
az afd profile create --profile-name "{{user.fd_name}}" --resource-group "{{user.resource_group}}" --sku Standard_AzureFrontDoor --output json
```
Full multi-step create (endpoint, origin-group, origin, route, probe) + Azure SDK fallback: [integration.md](references/integration.md).

### Add Custom Domain
```bash
az afd custom-domain create --custom-domain-name "{{user.custom_domain_name}}" --profile-name "{{user.fd_name}}" --resource-group "{{user.resource_group}}" --host-name "{{user.custom_domain}}" --certificate-type ManagedCertificate --minimum-tls-version TLS12 --output json
```
Associate with endpoint: `az afd route update ... --custom-domains ...`. Full: [integration.md](references/integration.md).

### Enable WAF Policy
```bash
az network front-door waf-policy create --name "{{user.waf_policy_name}}" --resource-group "{{user.resource_group}}" --mode Prevention --output json
```
Associate via `az afd security-policy create ...`. Full: [integration.md](references/integration.md).

### Delete Front Door Profile — Safety Gate
**MUST obtain explicit user confirmation (user types exact profile name) before deletion — deleting cuts all traffic to all endpoints.**
```bash
az afd profile show ... → confirm → az afd profile delete --profile-name "{{user.fd_name}}" --resource-group "{{user.resource_group}}" --output json
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
- DELETE profile (`az afd profile delete`) → **required**; all components traffic impact + Safety=0 → ABORT
- DELETE endpoint (`az afd endpoint delete`) → **required**; hostname traffic impact warned
- DELETE route (`az afd route delete`) → **required**; path/origin-group impact communicated
- PURGE cache (`az afd endpoint purge`) → **required**; load spike on origins warned
- DELETE custom domain → **required**; DNS resolution impact communicated
- CREATE profile / WAF / LIST → recommended

### Command Family Enforcement

This skill uses `az afd` commands (Front Door Standard/Premium). The deprecated `az network front-door` MUST NOT be used. Violation → spec_compliance = 0.

## L4 Auto-Feedback Loop

For autonomous operation on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-frontdoor-ops \
  --operation frontdoor_create \
  --command "az afd profile create --name {{user.profile_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"provisioningState": "Succeeded"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (create, endpoint_create): auto-feedback loop active
- **Risky operations** (delete): always bypass loop and require explicit human confirmation
- Healing policy: see [`scripts/self_healing/frontdoor_heal.json`](../../scripts/self_healing/frontdoor_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md) — SKU, components, FD vs AGW comparison
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md) — full `az afd` commands, SDK fallback, Recover table
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Front Door Docs](https://docs.microsoft.com/azure/frontdoor/)
- [Azure CLI Front Door Reference](https://docs.microsoft.com/cli/azure/afd)
- [Front Door Standard vs Premium](https://docs.microsoft.com/azure/frontdoor/standard-premium/tier-comparison)
