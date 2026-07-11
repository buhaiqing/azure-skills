# Integration Setup (Azure Site Recovery)

> SDK method names verified via `pip install azure-mgmt-recoveryservicessiterecovery==2.0.0` and Python introspection on 2026-07-11.

## Environment Setup

### Install Azure CLI (One-time per machine)

```bash
# macOS
brew install azure-cli

# Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
# Download from: https://aka.ms/installazurecliwindows

# Install Site Recovery extension
az extension add --name site-recovery
```

### Install Azure SDK for Python

```bash
# Core packages
pip install azure-identity azure-mgmt-resource

# Site Recovery package
pip install azure-mgmt-recoveryservicessiterecovery

# Verify
python -c "from azure.mgmt.recoveryservicessiterecovery import SiteRecoveryManagementClient; print('ASR SDK OK')"
```

## Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_SUBSCRIPTION_ID` | Azure subscription GUID | Yes |
| `AZURE_TENANT_ID` | Azure AD tenant GUID | Yes |
| `AZURE_CLIENT_ID` | Service Principal app ID | Yes |
| `AZURE_CLIENT_SECRET` | Service Principal secret | Yes |

## Azure CLI Authentication

```bash
# Login (interactive or device code)
az login

# Login with Service Principal (for automation)
az login --service-principal \
  --username "{{env.AZURE_CLIENT_ID}}" \
  --password "{{env.AZURE_CLIENT_SECRET}}" \
  --tenant "{{env.AZURE_TENANT_ID}}"

# Verify
az account show --output json
```

## Azure SDK Bootstrap

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.recoveryservicessiterecovery import SiteRecoveryManagementClient
import os

credential = DefaultAzureCredential()

# Site Recovery management client
# Note: resource_group_name and vault_name are NOT accepted in constructor;
# they must be passed to each operation method.
sr_client = SiteRecoveryManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

# The SDK also supports per-operation parameters:
# sr_client.replication_protected_items.get(
#     resource_group_name='...',
#     vault_name='...',
#     fabric_name='...',
#     protection_container_name='...',
#     replicated_protected_item_name='...'
# )
```

## RBAC Roles

| Role | Scope | Required For |
|------|-------|--------------|
| **Site Recovery Contributor** | Vault / Resource Group | Full DR management: enable replication, failover, failback |
| **Site Recovery Operator** | Vault / Resource Group | Execute failover and failback operations |
| **Site Recovery Reader** | Vault / Resource Group | Read-only access to replication status and jobs |
| **Virtual Machine Contributor** | Source VM | Enable replication (requires VM read access) |
| **Network Contributor** | Target VNet | Configure target network settings |

## Required Azure Resource Providers

```bash
# Register Recovery Services provider
az provider register --namespace Microsoft.RecoveryServices

# Verify registration
az provider show --namespace Microsoft.RecoveryServices --query "registrationState" --output json
```

## Network Requirements

Azure Site Recovery requires outbound HTTPS (443) connectivity from source VMs:
- `*.blob.core.windows.net` — Replication data storage
- `*.table.core.windows.net` — Replication metadata
- `*.queue.core.windows.net` — Replication queue
- `login.microsoftonline.com` — Authentication
- `*.backup.windowsazure.com` — ASR control plane

For VMs behind NSGs, use the `AzureSiteRecovery` service tag.
