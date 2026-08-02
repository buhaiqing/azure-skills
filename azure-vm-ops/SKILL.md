---
name: azure-vm-ops
description: >-
  Use when operating Azure Virtual Machine resources via Azure CLI or Azure SDK;
  user mentions "Virtual Machine", "VM", "Azure VM", "compute instance", or VM operations.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints and VMs.
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

# Azure Virtual Machine Operations Skill

## Overview

Azure Virtual Machines (VM) provides scalable, on-demand compute capacity for running applications in the cloud. This skill is an operational runbook with explicit scope, credential rules, pre-flight checks, dual-path execution (Azure CLI + Azure SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure Virtual Machine", "VM", "compute instance", "server"
- Task involves CRUD on **Virtual Machines** (create, show, start, stop, restart, delete, list)
- Keywords: vm, virtual machine, compute, instance, server, vm size, vm image
- Managing VM state, resizing, or deploying applications
- SSH/RDP access to VMs

### SHOULD NOT Use When
- Kubernetes clusters → delegate to: `azure-aks-ops`
- Container Instances → delegate to: `azure-containerinstance-ops`
- App Services → delegate to: `azure-appservice-ops`
- Billing only → delegate to: `azure-cost-ops`
- Network VNet only → delegate to: `azure-network-ops`

## Variable Convention

认证四件套 `{{env.AZURE_SUBSCRIPTION_ID/TENANT_ID/CLIENT_ID/SECRET}}` (NEVER ask user; fail if unset) 见 [azure-cli-conventions.md](../../azure-skill-generator/references/azure-cli-conventions.md#credential-sources-priority-order)；业务占位符见下。

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure region (e.g., eastus) |
| `{{user.vm_name}}` | User input | VM name; ask once |
| `{{user.vm_size}}` | User input | VM size (e.g., Standard_DS2_v2) |
| `{{user.image}}` | User input | OS image (e.g., UbuntuLTS, Win2019) |
| `{{user.new_vm_size}}` | User input | Target size for resize |
| `{{user.vnet_name}}` / `{{user.subnet_name}}` | User input | Existing VNet/subnet (optional) |
| `{{user.dns_name}}` | User input | Public IP DNS label (optional) |
| `{{user.admin_password}}` | User input | Windows admin password (secret, ask once) |
| `{{output.vm_id}}` | Last API response | Parse: `.id` from Azure CLI output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

通用 Pre-flight 五步（CLI/credentials/subscription/RG/Location）与 429/5xx 重试策略见 [azure-cli-conventions.md](../../azure-skill-generator/references/azure-cli-conventions.md)。

## Operations

Each operation: run the **Azure CLI (primary)**; on CLI failure retry up to 3×, then fall back to **Azure SDK for Python**. 完整命令与 SDK 回退见 [integration.md](references/integration.md)。

Full CLI commands + SDK fallback for all operations → [references/integration.md](references/integration.md).

| Op | Key flags |
|----|-----------|
| CREATE | `--image {{user.image}} --size {{user.vm_size}}`; validate: `az vm get-instance-view` |
| START / RESTART / STOP | `--resource-group {{user.resource_group}}`; STOP: use `--skip-shutdown` to keep billing |
| RESIZE | confirm deallocated first; `--size {{user.new_vm_size}}` |
| LIST | `--show-details` |
| RUN-COMMAND | `--command-id RunShellScript/RunPowerShellScript`; full commands: [integration.md](references/integration.md) |
| EXTENSION | `--name CustomScript --publisher Microsoft.Azure.Extensions`; common extensions: [core-concepts.md](references/core-concepts.md) |
| DELETE | **Safety Gate**: confirm exact VM name → `az vm delete --yes`; `--force-deletion` removes NIC/disks/public IP |

## Recovery (HALT vs Retry)

| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| QuotaExceeded | HALT; request quota increase |
| VMSizeNotAvailable | Suggest alternative VM size |
| Throttling (429) | Backoff, retry 3× |
| 5xx Internal | Retry 3×, then HALT |
| ImageNotFound | Suggest valid image |
| VNetNotFound | HALT; create VNet first |
| CommandTimeout (RunCommand) | Increase timeout; retry with shorter script |
| ScriptExecutionFailed | Fix script syntax; check VM logs |
| VMNotRunning | Start VM first |
| AccessDenied | Check RBAC permissions |
| AgentNotReady | Wait for VM agent to start |

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate.
See `AGENTS.md §3–§8` for the spec.

Risk tiers: R0 read / R1 mutable / R2 destructive — see [`scripts/risk_tiers.json`](../scripts/risk_tiers.json); enforced by auto_feedback_loop.

| Parameter | Value |
|-----------|-------|
| GCL | **required** |
| max_iterations | 2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE (`az vm delete`) → **required**; Safety=0 → ABORT
- STOP/DEALLOCATE (`az vm stop --skip-deallocation?`) → **required**; Safety=0 → ABORT
- RESIZE (`az vm resize`) → **required**; confirm VM state before mutation
- CREATE (`az vm create`) → **required**; validate pre-flight + idempotency
- START/RESTART/RUNCOMMAND → recommended

## L4 Auto-Feedback Loop

For autonomous operation without a human gate on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-vm-ops \
  --operation vm_create \
  --command "az vm create --name {{user.vm_name}} --resource-group {{user.resource_group}} --location {{user.location}} ..." \
  --desired-state '{"statuses[1].displayStatus": "VM running"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (create, start, restart, resize): auto-feedback loop active — observes actual VM state, diffs against desired, self-heals if non-running
- **Risky operations** (delete, stop/deallocate): always bypass the loop and require explicit human confirmation — safety gate cannot be overridden
- Healing policy: see [`scripts/self_healing/vm_heal.json`](../../scripts/self_healing/vm_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)



> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
