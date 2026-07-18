---
name: azure-backup-ops
description: >-
  Use when operating Azure Backup / Recovery Services resources via Azure CLI
  or Azure SDK; user mentions "Backup", "Recovery Services", "vault",
  "backup policy", "restore point", "stop protection", "soft-delete",
  "backup job", "backup item", or "backup failure".
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials
  (Service Principal), network access to Azure management endpoints and
  Recovery Services vault data-plane endpoints.
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

# Azure Backup / Recovery Services Operations Skill

## Overview

Azure Backup protects workloads (VMs, SQL, SAP HANA, AKS, Azure Files) via Recovery Services vaults. This skill handles vault operations, backup configuration, policy management, restore, and failure RCA. Keep this file concise; load `references/` for commands, SDK patterns, and RCA rules.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure Backup", "Recovery Services vault", "backup policy", "restore point"
- Task involves CRUD on **Recovery Services vaults** or **backup items**
- Keywords: backup, restore, vault, recovery point, protection policy, backup job, soft-delete, backup failure
- Troubleshooting backup failures (VM snapshot timeout, SQL log chain break, network errors)

### SHOULD NOT Use When
- VM-specific backup settings → delegate to: `azure-vm-ops`
- SQL DB backup → delegate to: `azure-sqldb-ops`
- AKS backup → delegate to: `azure-aks-ops`
- Monitoring backup alerts → delegate to: `azure-monitor-ops`
- Backup storage account → delegate to: `azure-blobstorage-ops`
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
| `{{user.location}}` | User input | Azure region (e.g., eastus) |
| `{{user.item_name}}` | User input | Backup item name |
| `{{user.policy_name}}` | User input | Backup policy name |
| `{{user.container_name}}` | User input | Protection container name |
| `{{user.vm_id}}` | User input | VM resource ID for backup config |
| `{{user.vm_name}}` | User input | VM name (for delegate to azure-vm-ops) |
| `{{user.recovery_point_name}}` | User input | Recovery point name (rp-name) |
| `{{user.storage_account}}` | User input | Storage account for restore |
| `{{user.job_name}}` | User input | Backup job name |
| `{{output.vault_id}}` | Last API response | Parse from CLI output |

## Execution Flow

Every operation follows: **Pre-flight → Execute → Validate → Recover**. See `references/core-concepts.md` for pre-flight tables, `references/troubleshooting.md` for recovery, `references/cli-commands.md` for detailed CLI commands.

### Operation: Create Recovery Services Vault
Pre-flight: verify RG exists, location valid, name available. See [`references/cli-commands.md`](references/cli-commands.md#create-recovery-services-vault).

### Operation: Configure Backup for VM
**Delegate**: First obtain VM resource ID via `azure-vm-ops` (`az vm show --name "{{user.vm_name}}" -g "{{user.resource_group}}" --query id -o tsv`), then execute. See [`references/cli-commands.md`](references/cli-commands.md#configure-backup-for-vm).

### Operation: Show Backup Status
See [`references/cli-commands.md`](references/cli-commands.md#show-backup-status).

### Operation: List Recovery Points
See [`references/cli-commands.md`](references/cli-commands.md#list-recovery-points).

### Operation: Restore Backup
Pre-flight: verify recovery point exists (consistent state), confirm target RG/Location, check storage. See [`references/cli-commands.md`](references/cli-commands.md#restore-backup).

### Operation: Delete Recovery Services Vault
**Safety Gate**: Deleting a vault also deletes all backup data. MUST show vault details first and obtain explicit human confirmation — user must type exact vault name to confirm. Two-phase: `az backup vault show` → confirm → `az resource delete --ids`. See [`references/cli-commands.md`](references/cli-commands.md#delete-recovery-services-vault).

### Operation: Stop Protection / Delete Backup Data
**Safety Gate**: STOP PROTECTION and DELETE BACKUP DATA are destructive operations with data-loss risk. MUST show current protection state via `az backup item show`, then obtain explicit human confirmation — user must type exact vault + item name to confirm. Two modes: retain or delete backup data. See [`references/cli-commands.md`](references/cli-commands.md#stop-protection-and-delete-backup-data).

### Operation: Update Backup Policy
**Safety Gate**: Changing retention policy may permanently delete recovery points. Show current policy before updating and obtain confirmation. Two-phase: fetch policy JSON → edit → apply. See [`references/cli-commands.md`](references/cli-commands.md#update-backup-policy).

### Operation: List / Show Backup Jobs
See [`references/cli-commands.md`](references/cli-commands.md#list--show-backup-jobs).

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate. See `AGENTS.md §3–§8` for the spec.

| Parameter | Value |
|-----------|-------|
| GCL | **required** |
| max_iterations | 2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE BACKUP DATA / STOP PROTECTION → **required**; Safety=0 → ABORT
- DELETE VAULT → **required**; Safety=0 → ABORT
- RESTORE → **required**; verify recovery point before mutation
- CREATE VAULT → **required**; validate pre-flight + idempotency
- UPDATE POLICY → **required**; confirm retention changes
- SHOW / LIST / STATUS → recommended

## Reference Files

- [CLI Commands](references/cli-commands.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Backup Documentation](https://docs.microsoft.com/azure/backup/)
- [Azure CLI Backup Reference](https://docs.microsoft.com/cli/azure/backup)
- [Azure SDK Recovery Services](https://docs.microsoft.com/python/api/azure-mgmt-recoveryservices/)
- [Azure SDK Recovery Services Backup](https://docs.microsoft.com/python/api/azure-mgmt-recoveryservicesbackup/)

