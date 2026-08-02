---
name: azure-trafficmanager-ops
description: >-
  Use when operating Azure Traffic Manager resources via Azure CLI or Azure SDK;
  user mentions "Traffic Manager", "TM", "DNS load balancing", or "global routing".
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

# Azure Traffic Manager Operations Skill

## Overview

Azure Traffic Manager provides **DNS-based** global load balancing for routing traffic across multiple regions and endpoints. This skill is an operational runbook: scope, credential rules, dual-path execution (Azure CLI + Azure SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "Traffic Manager", "TM", "DNS load balancing", "global routing"
- Task involves CRUD on **Traffic Manager** resources
- Keywords: profile, endpoint, routing method, priority, weight, geographic, performance
- DNS-based traffic routing / global multi-region failover / latency-based routing

### SHOULD NOT Use When
- L4/L7 proxy load balancing → delegate to `azure-loadbalancer-ops` or `azure-appgateway-ops`
- CDN acceleration → delegate to `azure-frontdoor-ops`
- Billing only → delegate to `azure-cost-ops`

## Variable Convention

Auth env quad (`AZURE_SUBSCRIPTION_ID` / `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET`) is a common skeleton — see [Credential Sources & Priority Order](../../azure-skill-generator/references/azure-cli-conventions.md#credential-sources-priority-order). Never ask the user; fail if unset.

Business placeholders (ask once, reuse):
- `{{user.resource_group}}` — target Resource Group
- `{{user.tm_name}}` — Traffic Manager profile name
- `{{user.tm_dns_name}}` — globally-unique DNS label (`{{user.tm_dns_name}}.trafficmanager.net`)
- `{{output.tm_id}}` — parsed `.id` from the last API/CLI response

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

Pre-flight checks (CLI availability, credential validity, subscription, Resource Group existence, DNS-name uniqueness) and the retry/backoff policy (CLI retries up to 3× before SDK fallback) are defined in [azure-cli-conventions.md](../../azure-skill-generator/references/azure-cli-conventions.md). Full commands and SDK fallback for every operation are in [integration.md](references/integration.md).

## Operations

### Create Profile
```bash
az network traffic-manager profile create \
  --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" \
  --routing-method Performance --unique-dns-name "{{user.tm_dns_name}}" \
  --ttl 30 --protocol HTTPS --port 443 --path "/" --output json
```
完整命令（Priority/Weighted/Geographic 变体）与 SDK 回退见 [integration.md](references/integration.md)。

### Add Endpoint
```bash
az network traffic-manager endpoint create \
  --name "endpoint-1" --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" --type azureEndpoints \
  --target-resource-id "{{user.target_resource_id}}" --endpoint-status enabled --output json
```
外部/嵌套端点、`--priority` / `--weight` / `--geo-mapping` 等变体见 [integration.md](references/integration.md)。

### Update Endpoint Status
```bash
az network traffic-manager endpoint update \
  --name "endpoint-1" --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" --endpoint-status enabled --output json
```
`enabled` / `disabled` 切换及完整参数见 [integration.md](references/integration.md)。

### Check Health
```bash
az network traffic-manager profile show \
  --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" --output json
```
端点健康状态（`endpointMonitorStatus`: Online/Degraded/Disabled/Inactive）见 [core-concepts.md](references/core-concepts.md)。

### Delete Profile — Safety Gate
**MUST obtain explicit user confirmation (type exact profile name) before deletion.** DNS routing is disrupted and the change is not reversible.
```bash
az network traffic-manager profile show --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" --output json
# confirm, then:
az network traffic-manager profile delete --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" --output json
```

## DNS Propagation Note
Traffic Manager is DNS-based — changes propagate per `--ttl` (default 30s; client DNS caches may be longer). Record the TTL value and propagation characteristics in the GCL trace.

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate. See `AGENTS.md §3–§8`.

| Parameter | Value |
|-----------|-------|
| GCL | **required** |
| max_iterations | 2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE profile → **required**; DNS impact warning + Safety=0 → ABORT
- DELETE endpoint → **required**; traffic reroute to remaining endpoints communicated
- DISABLE last healthy endpoint → **required**; degradation warning + Safety=0 → ABORT
- CHANGE routing method → **required**; traffic redistribution impact communicated
- CREATE / ADD / ENABLE / UPDATE → recommended

## L4 Auto-Feedback Loop

For autonomous operation on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-trafficmanager-ops \
  --operation profile_create \
  --command "az trafficmanager profile create --name {{user.profile_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"provisioningState": "Succeeded"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (profile_create, endpoint_update): auto-feedback loop active
- **Risky operations** (delete): always bypass loop and require explicit human confirmation
- Healing policy: see [`scripts/self_healing/trafficmanager_heal.json`](../../scripts/self_healing/trafficmanager_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files
- [Core Concepts](references/core-concepts.md) — routing methods, endpoint types, monitor status
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md) — full CLI commands + SDK fallback
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also
- [Traffic Manager Docs](https://docs.microsoft.com/azure/traffic-manager/)
- [Azure CLI Traffic Manager Reference](https://docs.microsoft.com/cli/azure/network/traffic-manager)
- [Routing Methods](https://docs.microsoft.com/azure/traffic-manager/traffic-manager-routing-methods)

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
