# Integration Setup (Azure File Storage)

## Environment Setup

Azure File Storage operations require Azure CLI and Azure SDK.

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

# Storage management package (for file share management plane)
pip install azure-mgmt-storage

# Storage file share data plane (for file/directory operations)
pip install azure-storage-file-share

# Verify
python -c "from azure.storage.fileshare import ShareServiceClient; print('Azure File SDK OK')"
```

### Install AzCopy (Recommended for Large Transfers)

```bash
# macOS
brew install azcopy

# Linux
wget https://aka.ms/downloadazcopy-v10-linux
tar -xvf downloadazcopy-v10-linux
sudo cp ./azcopy_linux_amd64_*/azcopy /usr/bin/

# Windows
# Download from: https://aka.ms/downloadazcopy-v10-windows

# Verify
azcopy --version
```

## Credential Configuration

### Method A: Service Principal (Recommended for Automation)

```bash
# Create Service Principal
az ad sp create-for-rbac \
  --name "my-filestorage-automation-sp" \
  --role "Contributor" \
  --scopes "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --output json
```

Store credentials:
```bash
export AZURE_SUBSCRIPTION_ID="{{env.AZURE_SUBSCRIPTION_ID}}"
export AZURE_TENANT_ID="{{env.AZURE_TENANT_ID}}"
export AZURE_CLIENT_ID="{{env.AZURE_CLIENT_ID}}"
export AZURE_CLIENT_SECRET="{{env.AZURE_CLIENT_SECRET}}"
```

### Method B: Azure CLI Login (Interactive)

```bash
az login
az account set --subscription "{{env.AZURE_SUBSCRIPTION_ID}}"
az account show --output json
```

## Storage Account Access Methods

### Method 1: Account Key Access (Management Plane)

```bash
# Get storage account keys
az storage account keys list \
  --account-name "{{user.storage_account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Use key in share operations
az storage share list \
  --account-name "{{user.storage_account_name}}" \
  --account-key "$ACCOUNT_KEY" \
  --output json
```

### Method 2: Azure AD Authentication (Management Plane — SDK Only)

```bash
# Assign Storage Account Contributor role
az role assignment create \
  --assignee "{{user.principal_id}}" \
  --role "Storage Account Contributor" \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Storage/storageAccounts/{{user.storage_account_name}}"
```

### Method 3: SAS Token (Time-limited Access)

```bash
# Generate SAS token for file service
az storage share generate-sas \
  --name "{{user.share_name}}" \
  --account-name "{{user.storage_account_name}}" \
  --permissions rwdl \
  --expiry "{{user.expiry_date}}" \
  --output tsv

# Use SAS token
az storage share list \
  --account-name "{{user.storage_account_name}}" \
  --sas-token "{{output.sas_token}}" \
  --output json
```

## Python SDK Usage

### Authenticate and Create Client (Management Plane)

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.storage import StorageManagementClient
import os

credential = DefaultAzureCredential()
client = StorageManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)
```

### File Share Operations (Management Plane)

```python
# Create file share
from azure.mgmt.storage.models import FileShare
client.file_shares.create(
    resource_group_name='{{user.resource_group}}',
    account_name='{{user.storage_account_name}}',
    share_name='{{user.share_name}}',
    file_share=FileShare(
        share_quota={{user.quota_gb}},  # GB
        enabled_protocols='SMB'
    )
)

# List file shares
shares = client.file_shares.list(
    resource_group_name='{{user.resource_group}}',
    account_name='{{user.storage_account_name}}'
)
for share in shares:
    print(share.name, share.share_quota)

# Get file share
share = client.file_shares.get(
    resource_group_name='{{user.resource_group}}',
    account_name='{{user.storage_account_name}}',
    share_name='{{user.share_name}}'
)

# Update quota
client.file_shares.update(
    resource_group_name='{{user.resource_group}}',
    account_name='{{user.storage_account_name}}',
    share_name='{{user.share_name}}',
    file_share=FileShare(
        share_quota={{user.quota_gb}}  # new quota in GB
    )
)

# Delete file share
client.file_shares.delete(
    resource_group_name='{{user.resource_group}}',
    account_name='{{user.storage_account_name}}',
    share_name='{{user.share_name}}'
)

# Restore deleted share
from azure.mgmt.storage.models import DeletedShare
client.file_shares.restore(
    resource_group_name='{{user.resource_group}}',
    account_name='{{user.storage_account_name}}',
    share_name='{{user.share_name}}',
    deleted_share=DeletedShare(
        deleted_share_name='{{user.share_name}}',
        deleted_share_version='{{output.deleted_share_version}}'
    )
)
```

### File Share Data Plane Operations

```python
from azure.storage.fileshare import ShareServiceClient
from azure.identity import DefaultAzureCredential

# Using account key
service = ShareServiceClient.from_connection_string(
    "DefaultEndpointsProtocol=https;AccountName={{user.storage_account_name}};AccountKey={{output.account_key}};EndpointSuffix=core.windows.net"
)

# List directories and files
share_client = service.get_share_client('{{user.share_name}}')
files = share_client.list_directories_and_files()
for item in files:
    print(f'  {"[dir]" if item.is_directory else "[file]"} {item.name}')

# Upload file
from azure.storage.fileshare import ShareFileClient
file_client = ShareFileClient.from_connection_string(
    conn_str="...",
    share_name="{{user.share_name}}",
    file_path="remote/path/file.txt"
)
with open("local_file.txt", "rb") as source:
    file_client.upload_file(source)
```

## AzCopy Usage (Large Transfers)

### Upload to File Share

```bash
# Upload single file
azcopy copy "{{user.local_file}}" "https://{{user.storage_account_name}}.file.core.windows.net/{{user.share_name}}/{{user.path}}?{{output.sas_token}}"

# Upload directory
azcopy copy "{{user.local_dir}}" "https://{{user.storage_account_name}}.file.core.windows.net/{{user.share_name}}?{{output.sas_token}}" --recursive

# Upload with sync (mirror)
azcopy sync "{{user.local_dir}}" "https://{{user.storage_account_name}}.file.core.windows.net/{{user.share_name}}?{{output.sas_token}}" --recursive
```

### Download from File Share

```bash
# Download single file
azcopy copy "https://{{user.storage_account_name}}.file.core.windows.net/{{user.share_name}}/{{user.path}}?{{output.sas_token}}" "{{user.local_path}}"

# Download entire share
azcopy copy "https://{{user.storage_account_name}}.file.core.windows.net/{{user.share_name}}?{{output.sas_token}}" "{{user.local_dir}}" --recursive
```

## RBAC Roles for File Storage

| Role | Scope | Permissions |
|------|-------|-------------|
| **Storage Account Contributor** | Subscription/RG/Account | Full management plane access |
| **Storage File Data SMB Share Reader** | Account/Share | Read SMB share (AD auth) |
| **Storage File Data SMB Share Contributor** | Account/Share | Read, write SMB share (AD auth) |
| **Storage File Data SMB Share Elevated Contributor** | Account/Share | Full SMB + ACL (AD auth) |
| **Storage File Data Privileged Reader** | Account/Share | Read file data (preview) |
| **Storage File Data Privileged Contributor** | Account/Share | Full file data access (preview) |

```bash
# Assign RBAC role for file share management
az role assignment create \
  --assignee "{{user.principal_id}}" \
  --role "Storage Account Contributor" \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Storage/storageAccounts/{{user.storage_account_name}}"
```

## Soft Delete Configuration

```bash
# Enable soft delete for file shares
az storage account file-service-properties update \
  --account-name "{{user.storage_account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --enable-share-delete-retention true \
  --share-delete-retention-days 14 \
  --output json

# Check current soft delete settings
az storage account file-service-properties show \
  --account-name "{{user.storage_account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

## Enable Large File Shares

```bash
# Large file shares support up to 100 TiB
az storage account update \
  --name "{{user.storage_account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --enable-large-file-share \
  --output json
```

## Common Azure Regions for Storage

| Region Code | Display Name |
|-------------|--------------|
| eastus | East US |
| eastus2 | East US 2 |
| westus | West US |
| westus2 | West US 2 |
| westus3 | West US 3 |
| centralus | Central US |
| northeurope | North Europe |
| westeurope | West Europe |
| southeastasia | Southeast Asia |
| eastasia | East Asia |

## Quick Reference Commands

```bash
# Create SMB file share
az storage share create --name myshare --account-name mySA --quota 100

# List file shares
az storage share list --account-name mySA

# Show file share
az storage share show --name myshare --account-name mySA

# Update quota
az storage share update --name myshare --account-name mySA --quota 200

# Create snapshot
az storage share snapshot --name myshare --account-name mySA

# List shares with snapshots
az storage share list --account-name mySA --include-snapshots

# Delete file share (requires confirmation)
az storage share delete --name myshare --account-name mySA --delete-snapshots include

# Generate SAS token
az storage share generate-sas --name myshare --account-name mySA --permissions rwdl --expiry 2026-12-31T23:59:00Z

# Get share stats
az storage share stats --name myshare --account-name mySA

# Enable soft delete
az storage account file-service-properties update --account-name mySA --rg myRG --enable-share-delete-retention true --share-delete-retention-days 14
```
