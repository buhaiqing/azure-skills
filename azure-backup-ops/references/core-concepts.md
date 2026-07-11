# Azure Backup / Recovery Services Core Concepts

> SDK method names verified via `pip install azure-mgmt-recoveryservices==4.1.0 azure-mgmt-recoveryservicesbackup==10.0.0` and Python introspection.

## What is Azure Backup

- **Purpose**: Cloud-native backup service protecting VMs, SQL Server, SAP HANA, Azure Files, and AKS workloads
- **Category**: Backup / Disaster Recovery (DR)
- **Docs**: https://docs.microsoft.com/azure/backup/
- **Pricing**: https://azure.microsoft.com/pricing/details/backup/

## Primary Resources

| Resource | Description | Azure CLI Group |
|----------|-------------|-----------------|
| Recovery Services Vault | Backup management container | `az backup vault` |
| Backup Policy | Schedule + retention rules | `az backup policy` |
| Backup Item | Protected workload instance | `az backup item` |
| Recovery Point | Point-in-time backup snapshot | `az backup recoverypoint` |
| Backup Job | Backup/restore operation tracking | `az backup job` |
| Protection Container | Workload grouping (VM, SQL, etc.) | `az backup container` |

## Architecture & Limits

### Resource ID Format
```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.RecoveryServices/vaults/{vault-name}
```

### Backup Workload Types

| Workload | Backup Type | RPO | Restore Options |
|----------|-------------|-----|-----------------|
| Azure VM | Full (weekly) + Differential (daily) + Log | 15 min (log) | Create VM, Restore Disks, File-Level |
| SQL Server in Azure VM | Full (weekly) + Differential (daily) + Log | 15 min (log) | Database restore, File-Level |
| SAP HANA in Azure VM | Full (weekly) + Differential (daily) + Log | 15 min (log) | Database restore |
| Azure Files | Snapshot (daily/weekly) | 1 hour | File Share, Individual File |
| AKS | Cluster snapshot | Configurable | Cluster restore |

### Recovery Point Types

| Type | Consistency | Description |
|------|-------------|-------------|
| Crash-consistent | File system | VM power-off, no app data guarantee |
| App-consistent | Application + file system | VSS (Windows) / pre-post scripts (Linux) |
| File-system-consistent | File system | Linux with pre-post scripts |

### Soft-Delete

| State | Data Retention | Billing | Description |
|-------|---------------|---------|-------------|
| Enabled (default) | 14 days additional | Yes | Retains data after `delete-backup-data` |
| Disabled | Immediate deletion | No | Permanent deletion on stop protection |
| Undelete | Full retention restored | Yes | Recover within soft-delete window |

### Naming Constraints

| Resource | Rules |
|----------|-------|
| Vault Name | 2-50 chars, alphanumeric and hyphens |
| Policy Name | 1-150 chars, alphanumeric, spaces, hyphens |
| Backup Item | Auto-generated from workload name |

## SDK Operation Groups (Verified)

### azure.mgmt.recoveryservices (Vault Management)

| Operation Group | Key Methods |
|-----------------|-------------|
| `client.vaults` | `begin_create_or_update`, `get`, `list_by_resource_group`, `list_by_subscription_id`, `begin_delete`, `begin_update` |

### azure.mgmt.recoveryservicesbackup (Backup Operations)

| Operation Group | Key Methods |
|-----------------|-------------|
| `client.protected_items` | `create_or_update`, `get`, `delete` |
| `client.protection_policies` | `get`, `create_or_update`, `begin_delete` |
| `client.recovery_points` | `get`, `list` |
| `client.backups` | `trigger` |
| `client.restores` | `begin_trigger` |
| `client.backup_jobs` | `list` |
| `client.jobs` | `export` |
| `client.backup_protected_items` | `list` |
| `client.backup_policies` | `list` |
| `client.protection_containers` | `get`, `begin_register`, `unregister`, `refresh`, `inquire` |
| `client.backup_resource_vault_configs` | `get`, `put`, `update` |
| `client.backup_resource_storage_configs_non_crr` | `get`, `patch`, `update` |
| `client.item_level_recovery_connections` | `provision`, `revoke` |
| `client.backup_operation_statuses` | `get` |
| `client.validate_operation` | `begin_trigger` |

## Pre-flight Tables

### Create Vault
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show` | HALT; configure env |
| Resource Group exists | `az group show --name {{user.resource_group}}` | Create or suggest existing |
| Location valid | `az account list-locations --output json` | Suggest valid location |
| Name availability | `az backup vault check-name --name {{user.vault_name}}` | HALT; suggest unique name |

### Restore
| Check | Method | On Failure |
|-------|--------|------------|
| Recovery point exists | `az backup recoverypoint show` | HALT; list available points |
| RP consistency | Check `properties.consistencyType` | Warn if crash-consistent only |
| Target RG exists | `az group show --name {{user.restore_rg}}` | Create or suggest existing |
| Storage account | `az storage account show` | Create or suggest existing |

## LRO Polling

All `begin_*` SDK operations (create vault, restore, delete) are Long Running Operations.

| Parameter | Value |
|-----------|-------|
| Poll interval | 5 seconds |
| Max wait | 300 seconds (5 minutes) |
| Timeout action | HALT; report timeout error |

## Stop Protection / Delete Backup Data
| Check | Method | On Failure |
|-------|--------|------------|
| Current protection state | `az backup item show` | HALT; item not found |
| Soft-delete state | Check `properties.softDeleteRetentionDays` | Inform user of retention period |
| Exact name confirmation | User types vault + item name | HALT; confirmation required |
