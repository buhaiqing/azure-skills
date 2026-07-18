---
name: azure-site-recovery-ops
description: >-
  Use when operating Azure Site Recovery (ASR) / disaster recovery resources
  via Azure CLI or Azure SDK; user mentions "Site Recovery", "ASR",
  "replication", "failover", "failback", "recovery plan", "disaster recovery",
  "DR", "replicate", "re-protect", or "test failover".
license: MIT
compatibility: >-
  Azure CLI 2.0+ (az site-recovery extension), Azure SDK for Python (3.10+),
  valid Azure credentials (Service Principal), Recovery Services vault in
  source and target regions, network connectivity between sites.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-07-11"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Site Recovery (ASR) Operations Skill

## Overview

Azure Site Recovery orchestrates disaster recovery (DR) for Azure VMs, Hyper-V VMs, and physical servers by replicating workloads from a primary site to a secondary Azure region. This skill handles vault setup, replication configuration, failover (test/planned/unplanned), failback, recovery plans, and job monitoring. Keep this file concise; load `references/` for commands, SDK patterns, and RCA rules.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure Site Recovery", "ASR", "disaster recovery", "replication", "failover", "failback", "re-protect"
- Task involves CRUD on **Replication protected items**, **Recovery Plans**, **Replication policies**, **Replication fabrics**
- Keywords: site recovery, asr, dr, replicate, failover, failback, recovery plan, re-protect, test failover, commit failover
- Troubleshooting replication health, synchronization lag, failover failures

### SHOULD NOT Use When
- VM backup/restore only → delegate to: `azure-backup-ops`
- VM creation/modification for DR source → delegate to: `azure-vm-ops`
- VNet/NSG setup for target region → delegate to: `azure-vnet-ops`, `azure-nsg-ops`
- DNS changes after failover → delegate to: `azure-dns-ops`
- Monitoring DR alerts → delegate to: `azure-monitor-ops`
- Billing/cost analysis → delegate to: `azure-cost-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.vault_name}}` | User input | Recovery Services vault name |
| `{{user.source_location}}` | User input | Source Azure region (e.g., eastus) |
| `{{user.target_location}}` | User input | Target Azure region (e.g., westus) |
| `{{user.vm_name}}` | User input | Source VM name |
| `{{user.protected_item_name}}` | User input | Replication protected item name |
| `{{user.recovery_plan_name}}` | User input | Recovery plan name |
| `{{user.replication_policy_name}}` | User input | Replication policy name |
| `{{user.fabric_name}}` | User input | Replication fabric name |
| `{{user.protection_container_name}}` | User input | Protection container name |
| `{{output.protected_item_id}}` | Last API response | Parse from CLI output |

## Execution Flow

Every operation follows: **Pre-flight → Execute → Validate → Recover**. See `references/core-concepts.md` for pre-flight tables, `references/troubleshooting.md` for recovery, `references/core-concepts.md` for detailed CLI commands.

### Operation: Create Recovery Services Vault (DR-enabled)
Pre-flight: verify RG exists, location valid, name available. Use `az backup vault create` to create the vault, then enable Site Recovery by setting the vault's `properties.publicNetworkAccess` via `az resource update` or ARM template. See `references/core-concepts.md`.

### Operation: Enable Replication for Azure VM
**Delegate**: First obtain VM resource ID via `azure-vm-ops` (`az vm show --name "{{user.vm_name}}" -g "{{user.resource_group}}" --query id -o tsv`). Configure replication: source fabric → source container → target region. See `references/core-concepts.md`.

### Operation: Show Replication Status
See `references/core-concepts.md`.

### Operation: Test Failover
**Safety Gate**: Test failover creates test VMs in an isolated VNet. MUST confirm isolation target (VNet/failover network) and obtain explicit user approval before proceeding. After validation, cleanup test failover is mandatory. Two-phase: show protected item → confirm test network → execute (SDK only) → cleanup. **CLI not supported**: test failover and cleanup are only available via Azure SDK (`begin_test_failover` / `begin_test_failover_cleanup`). See `references/core-concepts.md`.

### Operation: Commit Failover
**Safety Gate**: Failover commit confirms the failover and stops replication. This is a PRODUCTION-AFFECTING operation. MUST show current protected item state, obtain explicit human confirmation — user must type exact protected item name to confirm. After commit, verify target VM is running. See `references/core-concepts.md`.

### Operation: Unplanned Failover
**Safety Gate**: Unplanned failover triggers immediate failover with potential data loss. MUST warn about RPO gap, show current replication health, obtain explicit human confirmation — user must type exact protected item name. Direction: primary → recovery. See `references/core-concepts.md`.

### Operation: Planned Failover
**Safety Gate**: Planned failover requires source VM to be running and syncs data before shutdown. MUST confirm source VM is accessible, show current sync status, obtain explicit human confirmation before proceeding. Direction: primary → recovery (or recovery → primary for failback). See `references/core-concepts.md`.

### Operation: Failback (Re-protect + Reverse Replicate)
**Safety Gate**: Failback involves multiple destructive steps (re-protect + reverse replicate). Each step requires separate confirmation. After failover commit, re-protect must be enabled before reverse replication. See `references/core-concepts.md`.

### Operation: Create Recovery Plan
Recovery plans orchestrate multi-VM failover order. Define groups, pre/post-scripts, and automation runbooks. See `references/core-concepts.md`.

### Operation: List / Show Jobs
See `references/core-concepts.md`.

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate. See `AGENTS.md §3–§8` for the spec.

| Parameter | Value |
|-----------|-------|
| GCL | **required** |
| max_iterations | 2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- TEST FAILOVER → **required**; Safety=0 → ABORT; cleanup mandatory
- COMMIT FAILOVER → **required**; Safety=0 → ABORT
- UNPLANNED FAILOVER → **required**; Safety=0 → ABORT; warn data loss
- PLANNED FAILOVER → **required**; Safety=0 → ABORT
- FAILBACK (REPROTECT) → **required**; Safety=0 → ABORT
- DELETE VAULT → **required**; Safety=0 → ABORT
- ENABLE REPLICATION → **required**; validate pre-flight + idempotency
- SHOW / LIST / STATUS → recommended

## L4 Auto-Feedback Loop

For autonomous operation on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-site-recovery-ops \
  --operation vault_create \
  --command "az site-recovery vault create --name {{user.vault_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"provisioningState": "Succeeded"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (vault_create): auto-feedback loop active
- **Risky operations** (delete): always bypass loop and require explicit human confirmation
- Healing policy: see [`scripts/self_healing/site-recovery_heal.json`](../../scripts/self_healing/site-recovery_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Site Recovery Documentation](https://docs.microsoft.com/azure/site-recovery/)
- [Azure CLI Site Recovery Reference](https://docs.microsoft.com/cli/azure/site-recovery)
- [Azure SDK Recovery Services](https://docs.microsoft.com/python/api/azure-mgmt-recoveryservicessiterecovery/)

