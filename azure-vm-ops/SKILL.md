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

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure region (e.g., eastus) |
| `{{user.vm_name}}` | User input | VM name; ask once |
| `{{user.vm_size}}` | User input | VM size (e.g., Standard_DS2_v2) |
| `{{user.image}}` | User input | OS image (e.g., UbuntuLTS, Win2019) |
| `{{output.vm_id}}` | Last API response | Parse: `.id` from Azure CLI output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create Virtual Machine

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show` | HALT; configure env |
| Subscription valid | `az account list --output json` | Suggest valid subscription |
| Resource Group exists | `az group show --name {{user.resource_group}}` | Create or suggest existing |
| Location valid | `az account list-locations --output json` | Suggest valid location |
| VM size available | `az vm list-skus --location {{location}}` | Suggest valid VM size |
| Image available | `az vm image list --location {{location}}` | Suggest valid image |
| Quota check | Verify CPU quota | HALT; request quota increase |
| VNet exists (if specified) | `az network vnet show` | HALT; create VNet first |

#### Execute — Azure CLI (Primary)
```bash
# Create simple Linux VM
az vm create \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --image Ubuntu2204 \
  --size "{{user.vm_size}}" \
  --admin-username azureuser \
  --generate-ssh-keys \
  --output json

# Create Windows VM
az vm create \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --image Win2022Datacenter \
  --size "{{user.vm_size}}" \
  --admin-username azureuser \
  --admin-password "{{user.admin_password}}" \
  --output json

# Create VM with existing VNet and subnet
az vm create \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --image Ubuntu2204 \
  --size "{{user.vm_size}}" \
  --vnet-name "{{user.vnet_name}}" \
  --subnet "{{user.subnet_name}}" \
  --admin-username azureuser \
  --generate-ssh-keys \
  --output json

# Create VM with public IP and DNS
az vm create \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --image Ubuntu2204 \
  --size "{{user.vm_size}}" \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-address-dns-name "{{user.dns_name}}" \
  --output json
```

#### Execute — Azure SDK (Fallback)
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
import os

credential = DefaultAzureCredential()
client = ComputeManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

# Create VM
vm = client.virtual_machines.begin_create_or_update(
    resource_group_name='{{user.resource_group}}',
    vm_name='{{user.vm_name}}',
    parameters={
        'location': '{{user.location}}',
        'os_profile': {
            'computer_name': '{{user.vm_name}}',
            'admin_username': 'azureuser',
            'linux_configuration': {
                'disable_password_authentication': True,
                'ssh': {
                    'public_keys': [{
                        'path': '/home/azureuser/.ssh/authorized_keys',
                        'key_data': '{{ssh_public_key}}'
                    }]
                }
            }
        },
        'hardware_profile': {'vm_size': '{{user.vm_size}}'},
        'storage_profile': {
            'image_reference': {
                'publisher': 'Canonical',
                'offer': 'UbuntuServer',
                'sku': '22_04-lts',
                'version': 'latest'
            },
            'os_disk': {
                'create_option': 'FromImage',
                'managed_disk': {'storage_account_type': 'Standard_LRS'}
            }
        },
        'network_profile': {
            'network_interfaces': [{
                'id': '{{nic_id}}',
                'primary': True
            }]
        }
    }
).result()
```

#### Validate
```bash
# Verify VM state
az vm show --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --output json

# Check provisioning state: should be "Succeeded"
# Check power state
az vm get-instance-view --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --output json

# Verify SSH connectivity (Linux)
ssh azureuser@{{vm_public_ip}}
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| QuotaExceeded | HALT; request quota increase |
| VMSizeNotAvailable | Suggest alternative VM size |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |
| ImageNotFound | Suggest valid image |
| VNetNotFound | HALT; create VNet first |

### Operation: Start VM

```bash
az vm start --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --output json
```

### Operation: Stop VM

```bash
# Stop (deallocate - stops billing)
az vm stop --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --output json

# Stop without deallocating (still billed)
az vm stop --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --skip-deallocation --output json
```

### Operation: Restart VM

```bash
az vm restart --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --output json
```

### Operation: Resize VM

```bash
# Check available sizes
az vm list-skus --location "{{user.location}}" --output json

# Resize VM
az vm resize \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --size "{{user.new_vm_size}}" \
  --output json
```

### Operation: List VMs

```bash
# List all VMs in subscription
az vm list --output json

# List VMs in resource group
az vm list --resource-group "{{user.resource_group}}" --output json

# List with details
az vm list --resource-group "{{user.resource_group}}" --show-details --output json
```

### Operation: Delete VM

**Safety Gate**: MUST obtain explicit user confirmation before deletion. All attached disks and data will be lost.

```bash
# Show VM before deletion
az vm show --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --output json

# Request confirmation - user must type exact VM name
# Then proceed with deletion:
az vm delete \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --yes \
  --output json

# Delete with all related resources (NIC, disks, public IP)
az vm delete \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --yes \
  --force-deletion \
  --output json
```

### Operation: Run Command on VM (Cloud Assistant)

Azure RunCommand allows executing commands on VMs without SSH/RDP login. This is Azure's "cloud assistant" feature for remote command execution.

#### Execute — Azure CLI (Primary)
```bash
# Execute shell script on Linux VM
az vm run-command invoke \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --command-id RunShellScript \
  --scripts "whoami" "hostname" "df -h" \
  --output json

# Execute PowerShell script on Windows VM
az vm run-command invoke \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --command-id RunPowerShellScript \
  --scripts "Get-Process" "Get-Service" \
  --output json

# Execute multi-line script
az vm run-command invoke \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --command-id RunShellScript \
  --scripts @- <<'EOF'
#!/bin/bash
apt update
apt install -y nginx
systemctl start nginx
systemctl enable nginx
EOF

# Check script execution status
az vm run-command show \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --run-command-name "{{command_name}}" \
  --output json
```

#### Execute — Azure SDK (Fallback)
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
import os

credential = DefaultAzureCredential()
client = ComputeManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

# Run command on VM
result = client.virtual_machine_run_commands.begin_create_or_update(
    resource_group_name='{{user.resource_group}}',
    vm_name='{{user.vm_name}}',
    run_command_name='my-run-command',
    parameters={
        'location': '{{user.location}}',
        'source': {
            'script': 'whoami && hostname && df -h'
        },
        'timeout_in_seconds': 3600
    }
).result()

# Get run command result
run_command = client.virtual_machine_run_commands.get(
    resource_group_name='{{user.resource_group}}',
    vm_name='{{user.vm_name}}',
    run_command_name='my-run-command'
)
```

#### Available Command IDs

| OS | Command ID | Description |
|----|------------|-------------|
| **Linux** | RunShellScript | Execute bash shell script |
| **Linux** | RunPowerShellScript | Execute PowerShell (if installed) |
| **Linux** | ifconfig | Network interface info |
| **Windows** | RunPowerShellScript | Execute PowerShell script |

#### Validate
```bash
# Verify command execution result
az vm run-command list \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# View execution output
az vm run-command show \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --run-command-name "{{command_name}}" \
  --query "instanceView" \
  --output json
```

#### Recover
| Error | Action |
|-------|--------|
| CommandTimeout | Increase timeout; retry with shorter script |
| ScriptExecutionFailed | Fix script syntax; check VM logs |
| VMNotRunning | Start VM first |
| AccessDenied | Check RBAC permissions |
| AgentNotReady | Wait for VM agent to start |

### Operation: Install VM Extension

VM Extensions are persistent agents that can run scripts or configure settings.

```bash
# Install CustomScript extension (persistent)
az vm extension set \
  --name CustomScript \
  --publisher Microsoft.Azure.Extensions \
  --vm-name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --settings '{"fileUris":["https://example.com/setup.sh"]}' \
  --protected-settings '{"commandToExecute":"bash setup.sh"}' \
  --output json

# Install Azure Monitor Agent
az vm extension set \
  --name AzureMonitorLinuxAgent \
  --publisher Microsoft.Azure.Monitor \
  --vm-name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}"

# List installed extensions
az vm extension list \
  --vm-name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Remove extension
az vm extension delete \
  --name CustomScript \
  --vm-name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}"
```

## VM Sizes Categories

| Category | Series | Use Case |
|----------|--------|----------|
| **General Purpose** | B, D, DS | Balanced CPU/memory |
| **Compute Optimized** | F, FS | High CPU ratio |
| **Memory Optimized** | E, ES | High memory ratio |
| **Storage Optimized** | L, LS | High disk throughput |
| **GPU** | N, NC, NV | GPU workloads |
| **High Performance** | H, HB | HPC workloads |

## Common VM Sizes

| Size | vCPUs | Memory | Use Case |
|------|-------|--------|----------|
| **Standard_B2s** | 2 | 4GB | Dev/test |
| **Standard_DS2_v2** | 2 | 7GB | Small production |
| **Standard_DS3_v2** | 4 | 14GB | Medium production |
| **Standard_D4s_v3** | 4 | 16GB | General purpose |
| **Standard_E2s_v3** | 2 | 16GB | Memory-intensive |
| **Standard_F2s_v2** | 2 | 4GB | Compute-intensive |

## Common VM Images

| Image | Publisher | Offer | SKU |
|-------|-----------|-------|-----|
| Ubuntu 22.04 LTS | Canonical | UbuntuServer | 22_04-lts |
| Ubuntu 20.04 LTS | Canonical | UbuntuServer | 20_04-lts |
| Windows Server 2022 | MicrosoftWindowsServer | WindowsServer | 2022-datacenter |
| Windows Server 2019 | MicrosoftWindowsServer | WindowsServer | 2019-datacenter |
| CentOS 8 | OpenLogic | CentOS | 8_5 |
| Debian 11 | Debian | Debian | 11 |
| RHEL 8 | RedHat | RHEL | 8_8 |

## VM Extensions

Common extensions:
| Extension | Purpose | CLI Command |
|-----------|---------|-------------|
| **VMAccessAgent** | Reset password/SSH | `az vm user reset-ssh` |
| **CustomScript** | Run scripts on VM | `az vm extension set --name CustomScript` |
| **AzureMonitorAgent** | Monitoring integration | `az vm extension set --name AzureMonitorLinuxAgent` |
| **AzureDiskEncryption** | Disk encryption | `az vm extension set --name AzureDiskEncryption` |

## Remote Command Execution (Cloud Assistant)

| Method | Description | Use Case |
|--------|-------------|----------|
| **RunCommand** | One-time command execution | Quick diagnostics, one-off tasks |
| **VM Extension** | Persistent agent with scripts | Long-running config, monitoring |
| **SSH/RDP** | Direct interactive access | Full interactive session |

## VM Power States

| State | Billing | Description |
|-------|---------|-------------|
| **Running** | Yes | VM is running |
| **Stopped (deallocated)** | No | VM stopped, billing stopped |
| **Stopped** | Yes | VM stopped, still billed |
| **Creating** | Yes | Provisioning |
| **Updating** | Yes | Configuration change |
| **Deleting** | No | Deletion in progress |

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate.
See `AGENTS.md §3–§8` for the spec.

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

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Virtual Machines Documentation](https://docs.microsoft.com/azure/virtual-machines/)
- [Azure CLI VM Reference](https://docs.microsoft.com/cli/azure/vm)
- [Azure SDK Compute Module](https://docs.microsoft.com/python/api/azure-mgmt-compute/)
