# CLI Commands — azure-backup-ops

> Detailed Azure CLI commands for Azure Backup / Recovery Services operations.
> SKILL.md references this file for command details; refer there for safety gates and flow.

## Create Recovery Services Vault

```bash
az backup vault create --name "{{user.vault_name}}" --resource-group "{{user.resource_group}}" --location "{{user.location}}" --output json
```

## Configure Backup for VM

Pre-requisite: obtain VM resource ID via `azure-vm-ops` first.

```bash
az backup protection enable-for-vm --resource-group "{{user.resource_group}}" --vault-name "{{user.vault_name}}" --vm "{{user.vm_id}}" --policy-name "{{user.policy_name}}" --output json
```

## Show Backup Status

```bash
az backup item show --resource-group "{{user.resource_group}}" --vault-name "{{user.vault_name}}" --container-name "{{user.container_name}}" --name "{{user.item_name}}" --output json
```

## List Recovery Points

```bash
az backup recoverypoint list --resource-group "{{user.resource_group}}" --vault-name "{{user.vault_name}}" --container-name "{{user.container_name}}" --item-name "{{user.item_name}}" --output json
```

## Restore Backup

```bash
az backup restore restore-disks --resource-group "{{user.resource_group}}" --vault-name "{{user.vault_name}}" --container-name "{{user.container_name}}" --item-name "{{user.item_name}}" --rp-name "{{user.recovery_point_name}}" --storage-account "{{user.storage_account}}" --output json
```

## List / Show Backup Jobs

```bash
az backup job list --resource-group "{{user.resource_group}}" --vault-name "{{user.vault_name}}" --output json
az backup job show --resource-group "{{user.resource_group}}" --vault-name "{{user.vault_name}}" --name "{{user.job_name}}" --output json
```

## Delete Recovery Services Vault

Two-phase: confirm vault exists, then delete via generic resource API.

```bash
# Phase 1: confirm vault exists
az backup vault show --name "{{user.vault_name}}" --resource-group "{{user.resource_group}}" --query id -o tsv

# Phase 2: delete (after human confirmation)
az resource delete --ids "{{output.vault_id}}" --output json
```

## Stop Protection and Delete Backup Data

```bash
# Stop protection (retain backup data)
az backup protection disable --resource-group "{{user.resource_group}}" --vault-name "{{user.vault_name}}" --container-name "{{user.container_name}}" --name "{{user.item_name}}" --retain-backup-data true --output json

# Stop protection and delete backup data
az backup protection disable --resource-group "{{user.resource_group}}" --vault-name "{{user.vault_name}}" --container-name "{{user.container_name}}" --name "{{user.item_name}}" --delete-backup-data true --yes --output json
```

## Update Backup Policy

Two-phase: fetch current policy JSON, edit, then apply.

```bash
# Phase 1: get current policy definition
az backup policy show --name "{{user.policy_name}}" --resource-group "{{user.resource_group}}" --vault-name "{{user.vault_name}}" --output json > /tmp/policy.json

# Phase 2: edit /tmp/policy.json then apply
az backup policy set --policy @/tmp/policy.json --resource-group "{{user.resource_group}}" --vault-name "{{user.vault_name}}" --output json
```
