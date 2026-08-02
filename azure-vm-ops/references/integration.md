# Integration Setup (Azure Virtual Machine)

## Environment Setup

Azure VM operations require Azure CLI, Azure SDK, and SSH/RDP clients.

### Install Azure CLI (One-time per machine)

```bash
# macOS
brew install azure-cli

# Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
# Download from: https://aka.ms/installazurecliwindows
```

### Install Azure SDK for Python

```bash
# Core packages
pip install azure-identity azure-mgmt-resource

# Compute-specific package
pip install azure-mgmt-compute

# Network package (for NIC/VNet operations)
pip install azure-mgmt-network

# Verify
python -c "from azure.mgmt.compute import ComputeManagementClient; print('Azure Compute SDK OK')"
```

### SSH Client Setup (Linux VMs)

```bash
# Generate SSH keys
ssh-keygen -t rsa -b 4096 -f ~/.ssh/azure_vm_key

# View public key
cat ~/.ssh/azure_vm_key.pub

# SSH to VM
ssh -i ~/.ssh/azure_vm_key azureuser@{{vm_public_ip}}
```

### RDP Client Setup (Windows VMs)

- Windows: Built-in mstsc
- macOS: Microsoft Remote Desktop from App Store
- Linux: Remmina or xrdp

## Credential Configuration

### Method A: Service Principal (Recommended for Automation)

```bash
# Create Service Principal
az ad sp create-for-rbac \
  --name "my-vm-automation-sp" \
  --role "Contributor" \
  --scopes "/subscriptions/{{subscription-id}}" \
  --output json
```

Store credentials:
```bash
export AZURE_SUBSCRIPTION_ID="{{subscription-id}}"
export AZURE_TENANT_ID="{{tenant-id}}"
export AZURE_CLIENT_ID="{{app-id}}"
export AZURE_CLIENT_SECRET="{{password}}"
```

### Method B: Azure CLI Login (Interactive)

```bash
az login
az account set --subscription "{{subscription-id}}"
az account show --output json
```

## VM Creation Prerequisites

### Check Available VM Sizes

```bash
# List all sizes in location
az vm list-skus --location "{{location}}" --output json

# Filter by size family: e.g. Standard_DS, Standard_E, Standard_F
az vm list-skus --location "{{user.location}}" --size "{{user.vm_size_family}}" --output json

# Check quota usage
az vm list-usage --location "{{location}}" --output json
```

### Check Available Images

```bash
# List popular images
az vm image list --output json

# Search Ubuntu images
az vm image list --publisher Canonical --offer UbuntuServer --output json

# Search Windows images
az vm image list --publisher MicrosoftWindowsServer --offer WindowsServer --output json

# List all images in location
az vm image list --location "{{location}}" --all --output json
```

### Create Prerequisite Resources

```bash
# Create resource group
az group create --name "{{rg}}" --location "{{location}}" --output json

# Create VNet and subnet (optional, or create with VM)
az network vnet create \
  --name "{{vnet}}" \
  --resource-group "{{rg}}" \
  --location "{{location}}" \
  --address-prefixes "10.0.0.0/16" \
  --subnet-name "{{subnet}}" \
  --subnet-prefixes "10.0.0.0/24" \
  --output json

# Create public IP (optional, or create with VM)
az network public-ip create \
  --name "{{pip}}" \
  --resource-group "{{rg}}" \
  --location "{{location}}" \
  --allocation-method Static \
  --dns-name "{{dns_name}}" \
  --output json
```

## Python SDK Usage

### Authenticate and Create Client

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
import os

compute_client = ComputeManagementClient(DefaultAzureCredential(), os.environ.get('AZURE_SUBSCRIPTION_ID'))
network_client = NetworkManagementClient(DefaultAzureCredential(), os.environ.get('AZURE_SUBSCRIPTION_ID'))
# client bootstrap: see ../../../azure-skill-generator/references/azure-sdk-usage.md#common-client-bootstrap
```

### Create VM with SDK

```python
# Create NIC first
nic = network_client.network_interfaces.begin_create_or_update(
    resource_group_name='{{rg}}',
    network_interface_name='{{nic_name}}',
    parameters={
        'location': '{{location}}',
        'ip_configurations': [{
            'name': 'ipconfig',
            'subnet': {'id': '{{subnet_id}}'},
            'public_ip_address': {'id': '{{pip_id}}'}
        }]
    }
).result()

# Create VM
vm = compute_client.virtual_machines.begin_create_or_update(
    resource_group_name='{{rg}}',
    vm_name='{{vm_name}}',
    parameters={
        'location': '{{location}}',
        'os_profile': {
            'computer_name': '{{vm_name}}',
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
                'publisher': '{{user.image_publisher}}',  # discover: az vm image list --publisher {{user.image_publisher}}
                'offer': '{{user.image_offer}}',
                'sku': '{{user.image_sku}}',
                'version': 'latest'
            },
            'os_disk': {
                'create_option': 'FromImage',
                'managed_disk': {'storage_account_type': 'Standard_LRS'}
            }
        },
        'network_profile': {
            'network_interfaces': [{'id': nic.id, 'primary': True}]
        }
    }
).result()
```

### VM Operations with SDK

```python
# Start VM
compute_client.virtual_machines.begin_start('{{rg}}', '{{vm_name}}').wait()

# Stop VM (deallocate)
compute_client.virtual_machines.begin_power_off('{{rg}}', '{{vm_name}}').wait()

# Restart VM
compute_client.virtual_machines.begin_restart('{{rg}}', '{{vm_name}}').wait()

# Get VM details
vm = compute_client.virtual_machines.get('{{rg}}', '{{vm_name}}')

# List VMs
vms = compute_client.virtual_machines.list_by_resource_group('{{rg}}')
```

### Run Command with SDK (Fallback)

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

## RBAC Roles for VMs

| Role | Permissions |
|------|-------------|
| **Contributor** | Full VM management |
| **Virtual Machine Contributor** | VM operations (no RBAC) |
| **Virtual Machine Administrator Login** | Admin SSH/RDP access |
| **Virtual Machine User Login** | User SSH/RDP access |

```bash
# Assign VM contributor role
az role assignment create \
  --assignee "{{user-or-sp-id}}" \
  --role "Virtual Machine Contributor" \
  --scope "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.Compute/virtualMachines/{{vm}}"
```

## SSH Key Management

### Generate SSH Key

```bash
# Generate new SSH key pair
ssh-keygen -t rsa -b 4096 -f ~/.ssh/azure_key -N ""

# Display public key
cat ~/.ssh/azure_key.pub

# Add to VM during creation
az vm create \
  --name "{{vm}}" \
  --resource-group "{{rg}}" \
  --ssh-key-value "$(cat ~/.ssh/azure_key.pub)"
```

### Reset SSH Key/Password

```bash
# Reset SSH key for existing VM
az vm user reset-ssh \
  --name "{{vm}}" \
  --resource-group "{{rg}}" \
  --username azureuser \
  --ssh-key-value "$(cat ~/.ssh/new_key.pub)"

# Reset password
az vm user update \
  --name "{{vm}}" \
  --resource-group "{{rg}}" \
  --username azureuser \
  --password "{{new_password}}"
```

## VM Extensions Setup

### Run Custom Script

```bash
# Install extension and run script
az vm extension set \
  --name CustomScript \
  --publisher Microsoft.Azure.Extensions \
  --vm-name "{{vm}}" \
  --resource-group "{{rg}}" \
  --settings '{"fileUris":["https://{{script_url}}"]}' \
  --protected-settings '{"commandToExecute":"bash {{script_name}}"}' \
  --output json
```

### Enable Azure Monitor Agent

```bash
az vm extension set \
  --name AzureMonitorLinuxAgent \
  --publisher Microsoft.Azure.Monitor \
  --vm-name "{{vm}}" \
  --resource-group "{{rg}}" \
  --output json
```

## Common Azure Regions for VMs

| Region Code | Display Name | Availability Zones |
|-------------|--------------|-------------------|
| eastus | East US | Yes |
| eastus2 | East US 2 | Yes |
| westus2 | West US 2 | Yes |
| centralus | Central US | Yes |
| westeurope | West Europe | Yes |
| northeurope | North Europe | Yes |
| southeastasia | Southeast Asia | Yes |
| eastasia | East Asia | Yes |

## Quick Reference Commands

```bash
# Discover: `az vm list-skus --location {{user.location}} --output json` and `az vm image list --publisher {{user.image_publisher}} --offer {{user.image_offer}} --sku {{user.image_sku}} --output json`
# Create Linux VM
az vm create --name {{user.vm_name}} --resource-group {{user.resource_group}} --location {{user.location}} --image {{user.image}} --size {{user.vm_size}} --admin-username {{user.admin_username}} --generate-ssh-keys

# Create Windows VM
az vm create --name {{user.vm_name}} --resource-group {{user.resource_group}} --location {{user.location}} --image {{user.image}} --size {{user.vm_size}} --admin-username {{user.admin_username}} --admin-password "{{user.admin_password}}"

# List VMs
az vm list --output json

# Show VM details
az vm show --name {{user.vm_name}} --resource-group {{user.resource_group}} --output json

# Start VM
az vm start --name {{user.vm_name}} --resource-group {{user.resource_group}}

# Stop VM (deallocate - stops billing)
az vm stop --name {{user.vm_name}} --resource-group {{user.resource_group}}

# Resize VM
az vm resize --name {{user.vm_name}} --resource-group {{user.resource_group}} --size {{user.new_vm_size}}

# Delete VM
az vm delete --name {{user.vm_name}} --resource-group {{user.resource_group}} --yes
```

## Project-based Setup (pyproject.toml)

```toml
[project]
name = "azure-vm-ops"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "azure-identity>=1.10.0",
    "azure-mgmt-resource>=21.0.0",
    "azure-mgmt-compute>=27.0.0",
    "azure-mgmt-network>=23.0.0",
]
```

## Full Command Reference (CLI)

> Primary commands referenced from `SKILL.md`. SDK fallbacks for create/run-command are in the sections above.

### Create VM

```bash
# Create simple Linux VM
az vm create \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --image "{{user.image}}" \
  --size "{{user.vm_size}}" \
  --admin-username azureuser \
  --generate-ssh-keys \
  --output json

# Create Windows VM
az vm create \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --image "{{user.image}}" \
  --size "{{user.vm_size}}" \
  --admin-username azureuser \
  --admin-password "{{user.admin_password}}" \
  --output json

# Create VM with existing VNet and subnet
az vm create \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --image "{{user.image}}" \
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
  --image "{{user.image}}" \
  --size "{{user.vm_size}}" \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-address-dns-name "{{user.dns_name}}" \
  --output json
```

### Validate Create

```bash
# Verify VM state
az vm show --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --output json

# Check provisioning state: should be "Succeeded"
az vm get-instance-view --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --output json

# Verify SSH connectivity (Linux)
ssh azureuser@{{vm_public_ip}}
```

### Start / Stop / Restart / Resize / List

```bash
# Start
az vm start --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --output json

# Stop (deallocate - stops billing)
az vm stop --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --output json

# Stop without deallocating (still billed)
az vm stop --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --skip-deallocation --output json

# Restart
az vm restart --name "{{user.vm_name}}" --resource-group "{{user.resource_group}}" --output json

# Resize
az vm resize \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --size "{{user.new_vm_size}}" \
  --output json

# List all VMs in subscription
az vm list --output json

# List VMs in resource group
az vm list --resource-group "{{user.resource_group}}" --output json

# List with details
az vm list --resource-group "{{user.resource_group}}" --show-details --output json
```

### Run Command (Cloud Assistant)

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

# Verify command execution result
az vm run-command list \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az vm run-command show \
  --name "{{user.vm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --run-command-name "{{command_name}}" \
  --query "instanceView" \
  --output json
```

### Delete VM (destructive — requires human confirmation)

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

### Extension (full CLI)

```bash
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