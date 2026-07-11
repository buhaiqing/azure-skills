# Azure Site Recovery (ASR) Core Concepts

> SDK method names verified via `pip install azure-mgmt-recoveryservicessiterecovery==2.0.0` and Python introspection on 2026-07-11.

## What is Azure Site Recovery

- **Purpose**: Cloud-native disaster recovery service that replicates Azure VMs, Hyper-V VMs, and physical servers between regions
- **Category**: Disaster Recovery (DR) / Business Continuity
- **Docs**: https://docs.microsoft.com/azure/site-recovery/
- **Pricing**: https://azure.microsoft.com/pricing/details/site-recovery/

## Primary Resources

| Resource | Description | Azure CLI Group | SDK Operation Group |
|----------|-------------|-----------------|---------------------|
| Recovery Services Vault | DR management container | `az backup vault` (CRUD) / `az site-recovery vault` (config) | `client.vaults` |
| Replication Fabric | Site representation (Azure/Hyper-V) | `az site-recovery fabric` | `client.replication_fabrics` |
| Protection Container | Logical container for replicated items | `az site-recovery protection-container` | `client.replication_protection_containers` |
| Replication Policy | RPO, retention, app-consistent snapshot settings | `az site-recovery policy` | `client.replication_policies` |
| Protected Item | Replicated workload instance | `az site-recovery protected-item` | `client.replication_protected_items` |
| Recovery Plan | Orchestrated failover sequence | `az site-recovery recovery-plan` | `client.replication_recovery_plans` |
| Recovery Point | Point-in-time snapshot for failover | `az site-recovery recovery-point` | `client.recovery_points` |
| Replication Job | Async operation tracker | `az site-recovery job` | `client.replication_jobs` |

## Architecture & Limits

### Resource ID Format
```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.RecoveryServices/vaults/{vault-name}
```

### Failover Types

| Type | Data Loss | Direction | Use Case | Source VM State |
|------|-----------|-----------|----------|-----------------|
| **Test Failover** | None | Primary → Recovery | DR drill, validation | Running (no impact) |
| **Planned Failover** | None (zero data loss) | Primary → Recovery / Recovery → Primary | Planned migration, maintenance | Running (synced, then shutdown) |
| **Unplanned Failover** | Possible (up to RPO) | Primary → Recovery | Disaster, unplanned outage | May be down |
| **Failback (Re-protect + Reverse)** | Possible | Recovery → Primary | Return to primary after failover | Recovery VM must be running |

### Naming Constraints

| Resource | Rules |
|----------|-------|
| Vault Name | 2-50 chars, alphanumeric and hyphens |
| Fabric Name | Auto-generated; typically "eastus" or "HyperVSite" |
| Protected Item | Auto-generated from VM name |
| Recovery Plan | 1-150 chars, alphanumeric, spaces, hyphens |

## SDK Operation Groups (Verified)

### azure.mgmt.recoveryservicessiterecovery (Site Recovery Management)

**Client**: `from azure.mgmt.recoveryservicessiterecovery import SiteRecoveryManagementClient`

| Operation Group | Key Methods |
|-----------------|-------------|
| `client.replication_protected_items` | `begin_create`, `begin_planned_failover`, `begin_unplanned_failover`, `begin_test_failover`, `begin_test_failover_cleanup`, `begin_failover_commit`, `begin_failover_cancel`, `begin_reprotect`, `begin_apply_recovery_point`, `begin_delete`, `begin_purge`, `begin_update`, `begin_add_disks`, `begin_remove_disks`, `begin_repair_replication`, `begin_resolve_health_errors`, `begin_update_mobility_service`, `begin_switch_provider`, `get`, `list` |
| `client.replication_protection_containers` | `get`, `list`, `begin_create`, `begin_delete`, `begin_discover_protectable_item`, `begin_switch_protection`, `list_by_replication_fabrics` |
| `client.replication_protection_container_mappings` | `get`, `list`, `begin_create`, `begin_delete`, `begin_purge`, `begin_update` |
| `client.replication_recovery_plans` | `begin_create`, `begin_unplanned_failover`, `begin_planned_failover`, `begin_test_failover`, `begin_test_failover_cleanup`, `begin_failover_commit`, `begin_failover_cancel`, `begin_reprotect`, `begin_delete`, `begin_update`, `get`, `list` |
| `client.replication_fabrics` | `begin_create`, `get`, `list`, `begin_check_consistency`, `begin_delete`, `begin_purge`, `begin_migrate_to_aad`, `begin_reassociate_gateway`, `begin_renew_certificate` |
| `client.replication_jobs` | `get`, `list`, `begin_cancel`, `begin_restart`, `begin_resume`, `begin_export` |
| `client.replication_networks` | `get`, `list`, `list_by_replication_fabrics` |
| `client.replication_network_mappings` | `begin_create`, `get`, `list`, `begin_delete`, `begin_update` |
| `client.recovery_points` | `get`, `list_by_replication_protected_items` |
| `client.replication_protection_intents` | `create`, `get`, `list` |
| `client.replication_alert_settings` | `create`, `get`, `list` |
| `client.replication_policies` | `begin_create`, `get`, `list`, `begin_delete`, `begin_update` |

## Pre-flight Tables

### Create Vault (DR-enabled)
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show` | HALT; configure env |
| Resource Group exists | `az group show --name {{user.resource_group}}` | Create or suggest existing |
| Location valid | `az account list-locations --output json` | Suggest valid location |
| Name availability | `az backup vault check-name --name {{user.vault_name}}` | HALT; suggest unique name |

### Enable Replication
| Check | Method | On Failure |
|-------|--------|------------|
| Source VM exists | `az vm show --name {{user.vm_name}} -g {{user.resource_group}}` | HALT; VM not found |
| Source VM location | `az vm show --query location` | Must match source region |
| Target region valid | `az account list-locations --output json` | Suggest valid target location |
| Target RG exists | `az group show --name {{user.target_rg}}` | Create or suggest existing |
| Target VNet exists | `az network vnet show -g {{user.target_rg}} --name {{user.target_vnet}}` | HALT; create VNet first (delegate to azure-vnet-ops) |
| Fabric exists | `az site-recovery fabric show --name {{user.fabric_name}}` | HALT; create fabric first |
| Protection container exists | `az site-recovery protection-container show --name {{user.protection_container_name}} --fabric-name {{user.fabric_name}}` | HALT; discover protection container first |

### Test Failover
| Check | Method | On Failure |
|-------|--------|------------|
| Protected item exists | `az site-recovery protected-item show` | HALT; enable replication first |
| Replication health | Check `properties.replicationHealth` | Warn if unhealthy |
| Test VNet isolated | `az network vnet show --name {{user.test_vnet}}` | HALT; specify isolated VNet |
| Cleanup readiness | Verify no prior test failover pending | HALT; cleanup first |

### Failover Commit
| Check | Method | On Failure |
|-------|--------|------------|
| Protected item state | `az site-recovery protected-item show` | HALT; item not found |
| Failover direction | Check `properties.activeLocation` | Confirm correct direction |
| Replication paused | Verify failover committed state | HALT; unplanned failover first |

## CLI Commands (Primary)

### Vault Management

`az site-recovery vault` provides Site Recovery-specific vault configuration commands:

```bash
# List vaults in a resource group
az site-recovery vault list \
  --resource-group "{{user.resource_group}}" \
  --output json

# Show vault details
az site-recovery vault show \
  --name "{{user.vault_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Update vault properties (e.g., add tags)
az site-recovery vault update \
  --name "{{user.vault_name}}" \
  --resource-group "{{user.resource_group}}" \
  --tags environment=dr \
  --output json

# Delete vault (DESTRUCTIVE — requires confirmation)
az site-recovery vault delete \
  --name "{{user.vault_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

Note: `az backup vault` is used for initial vault CRUD (create); `az site-recovery vault` handles post-creation configuration and management.

### Create Recovery Services Vault (DR-enabled)
```bash
# Step 1: Create vault using Backup CLI (only CLI available for vault CRUD)
az backup vault create \
  --name "{{user.vault_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.source_location}}" \
  --output json

# Step 2: Enable Site Recovery capability on the vault
# Update vault properties to enable ASR (publicNetworkAccess + sku)
az resource update \
  --ids "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.RecoveryServices/vaults/{{user.vault_name}}" \
  --set properties.publicNetworkAccess="Enabled" \
  --api-version 2022-10-01 \
  --output json

# Alternatively, use an ARM template for full vault + ASR enablement
# See: https://docs.microsoft.com/azure/site-recovery/site-recovery-create-recovery-services-vault
```

### Enable Replication for Azure VM
```bash
# Step 1: Get VM ID
VM_ID=$(az vm show \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query id -o tsv)

# Step 2: Enable replication using --provider-details JSON
az site-recovery protected-item create \
  --fabric-name "{{user.fabric_name}}" \
  --protection-container "{{user.protection_container_name}}" \
  --name "{{user.protected_item_name}}" \
  --resource-group "{{user.resource_group}}" \
  --vault-name "{{user.vault_name}}" \
  --policy-name "{{user.replication_policy_name}}" \
  --provider-details '{
    "instanceType": "A2A",
    "sourceVmId": "'"$VM_ID"'",
    "targetResourceGroupId": "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.target_rg}}",
    "targetLocation": "{{user.target_location}}",
    "targetVnetId": "{{user.target_vnet_id}}"
  }' \
  --output json
```

### Show Replication Status
```bash
az site-recovery protected-item show \
  --fabric-name "{{user.fabric_name}}" \
  --protection-container "{{user.protection_container_name}}" \
  --name "{{user.protected_item_name}}" \
  --resource-group "{{user.resource_group}}" \
  --vault-name "{{user.vault_name}}" \
  --output json

# Extract health
az site-recovery protected-item show \
  --fabric-name "{{user.fabric_name}}" \
  --protection-container "{{user.protection_container_name}}" \
  --name "{{user.protected_item_name}}" \
  --resource-group "{{user.resource_group}}" \
  --vault-name "{{user.vault_name}}" \
  --query "properties.replicationHealth" \
  -o tsv
```

### Test Failover

Test failover and cleanup are **only available via Azure SDK** — CLI not supported.

**SDK method**: `begin_test_failover()` / `begin_test_failover_cleanup()`

```python
from azure.mgmt.recoveryservicessiterecovery import SiteRecoveryManagementClient
from azure.identity import DefaultAzureCredential
import os

credential = DefaultAzureCredential()
client = SiteRecoveryManagementClient(
    credential,
    subscription_id=os.environ['AZURE_SUBSCRIPTION_ID']
)

# Execute test failover
client.replication_protected_items.begin_test_failover(
    resource_group_name='{{user.resource_group}}',
    vault_name='{{user.vault_name}}',
    fabric_name='{{user.fabric_name}}',
    protection_container_name='{{user.protection_container_name}}',
    replicated_protected_item_name='{{user.protected_item_name}}',
    testfailover_input={
        "properties": {
            "failover_direction": "PrimaryToRecovery",
            "network_id": "{{user.test_vnet_id}}",
            "network_type": "VmNetworkAsInput"
        }
    }
).result()

# Cleanup test failover (mandatory after validation)
client.replication_protected_items.begin_test_failover_cleanup(
    resource_group_name='{{user.resource_group}}',
    vault_name='{{user.vault_name}}',
    fabric_name='{{user.fabric_name}}',
    protection_container_name='{{user.protection_container_name}}',
    replicated_protected_item_name='{{user.protected_item_name}}',
    cleanup_input={
        "properties": {
            "comments": "Test failover validated and cleaned up"
        }
    }
).result()
```

### Unplanned Failover
```bash
az site-recovery protected-item unplanned-failover \
  --fabric-name "{{user.fabric_name}}" \
  --protection-container "{{user.protection_container_name}}" \
  --name "{{user.protected_item_name}}" \
  --resource-group "{{user.resource_group}}" \
  --vault-name "{{user.vault_name}}" \
  --failover-direction PrimaryToRecovery \
  --output json
```

### Commit Failover
```bash
az site-recovery protected-item failover-commit \
  --fabric-name "{{user.fabric_name}}" \
  --protection-container "{{user.protection_container_name}}" \
  --name "{{user.protected_item_name}}" \
  --resource-group "{{user.resource_group}}" \
  --vault-name "{{user.vault_name}}" \
  --output json
```

### Planned Failover
```bash
az site-recovery protected-item planned-failover \
  --fabric-name "{{user.fabric_name}}" \
  --protection-container "{{user.protection_container_name}}" \
  --name "{{user.protected_item_name}}" \
  --resource-group "{{user.resource_group}}" \
  --vault-name "{{user.vault_name}}" \
  --failover-direction PrimaryToRecovery \
  --output json
```

### Failback (Re-protect)
```bash
# Step 1: Re-protect (reverse replicate)
az site-recovery protected-item reprotect \
  --fabric-name "{{user.fabric_name}}" \
  --protection-container "{{user.protection_container_name}}" \
  --name "{{user.protected_item_name}}" \
  --resource-group "{{user.resource_group}}" \
  --vault-name "{{user.vault_name}}" \
  --output json

# Step 2: Planned failover back to primary
az site-recovery protected-item planned-failover \
  --fabric-name "{{user.fabric_name}}" \
  --protection-container "{{user.protection_container_name}}" \
  --name "{{user.protected_item_name}}" \
  --resource-group "{{user.resource_group}}" \
  --vault-name "{{user.vault_name}}" \
  --failover-direction RecoveryToPrimary \
  --output json
```

### Create Recovery Plan
```bash
az site-recovery recovery-plan create \
  --name "{{user.recovery_plan_name}}" \
  --resource-group "{{user.resource_group}}" \
  --vault-name "{{user.vault_name}}" \
  --fabric-name "{{user.fabric_name}}" \
  --source-fabric-location "{{user.source_location}}" \
  --output json

# Add groups and protected items after creation
az site-recovery recovery-plan update \
  --name "{{user.recovery_plan_name}}" \
  --resource-group "{{user.resource_group}}" \
  --vault-name "{{user.vault_name}}" \
  --add-group \
  --group-type "Boot" \
  --protected-items "{{user.protected_item_name}}" \
  --output json
```

### List Jobs
```bash
az site-recovery job list \
  --resource-group "{{user.resource_group}}" \
  --vault-name "{{user.vault_name}}" \
  --output json

# Show specific job
az site-recovery job show \
  --name "{{user.job_name}}" \
  --resource-group "{{user.resource_group}}" \
  --vault-name "{{user.vault_name}}" \
  --output json
```

## LRO Polling

All `begin_*` SDK operations (create vault, enable replication, failover, failback) are Long Running Operations.

| Parameter | Value |
|-----------|-------|
| Poll interval | 5 seconds |
| Max wait | 600 seconds (10 minutes) for failover; 300 seconds (5 minutes) for other operations |
| Timeout action | HALT; report timeout error; check job status via `az site-recovery job list` |

## Replication Health States

| State | Meaning | Action |
|-------|---------|--------|
| Healthy | Replication normal | No action |
| Warning | Sync lag > RPO threshold | Check network; increase bandwidth |
| Critical | Replication stalled or failed | Check source VM state; repair replication |
| Not Applicable | Failover committed or replication disabled | N/A |
