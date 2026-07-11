# Integration Setup (Azure Backup / Recovery Services)

> SDK method names verified via `pip install azure-mgmt-recoveryservices==4.1.0 azure-mgmt-recoveryservicesbackup==10.0.0` and Python introspection on 2026-07-11.

## Environment Setup

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

# Recovery Services packages
pip install azure-mgmt-recoveryservices
pip install azure-mgmt-recoveryservicesbackup

# Verify
python -c "from azure.mgmt.recoveryservices import RecoveryServicesClient; print('RS SDK OK')"
python -c "from azure.mgmt.recoveryservicesbackup import RecoveryServicesBackupClient; print('RS Backup SDK OK')"
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
from azure.mgmt.recoveryservices import RecoveryServicesClient
from azure.mgmt.recoveryservicesbackup import RecoveryServicesBackupClient
import os

credential = DefaultAzureCredential()

# Vault management client
rs_client = RecoveryServicesClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

# Backup operations client
rs_backup_client = RecoveryServicesBackupClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)
```

## RBAC Roles

| Role | Scope | Required For |
|------|-------|--------------|
| **Backup Contributor** | Vault / Resource Group | Create/configure backup, restore, manage policies |
| **Backup Operator** | Vault / Resource Group | View backup status, trigger backup, restore |
| **Backup Reader** | Vault / Resource Group | Read-only access to backup status and jobs |
| **Virtual Machine Contributor** | VM | Configure VM backup (requires VM read access) |
| **Storage Account Contributor** | Storage Account | Restore disks to storage account |

## Required Azure Resource Providers

```bash
# Register Recovery Services provider
az provider register --namespace Microsoft.RecoveryServices

# Verify registration
az provider show --namespace Microsoft.RecoveryServices --query "registrationState" --output json
```

## Network Requirements

Azure Backup requires outbound HTTPS (443) connectivity to:
- `*.backup.windowsazure.com` — Backup data plane
- `*.blob.core.windows.net` — Backup storage
- `*.queue.core.windows.net` — Backup queue
- `login.microsoftonline.com` — Authentication

For VMs behind NSGs, use the `AzureBackup` service tag.
