# Integration Setup (Azure Blob Storage)

## Environment Setup

Azure Blob Storage operations require Azure CLI and Azure SDK.

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

# Storage-specific packages
pip install azure-mgmt-storage
pip install azure-storage-blob

# Verify
python -c "from azure.storage.blob import BlobServiceClient; print('Azure Blob SDK OK')"
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
  --name "my-storage-automation-sp" \
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

## Storage Account Access Methods

### Method 1: Account Key Access

```bash
# Get storage account keys
az storage account keys list \
  --account-name "{{storage_account}}" \
  --resource-group "{{rg}}" \
  --output json

# Use key in operations
az storage container list \
  --account-name "{{storage_account}}" \
  --account-key "{{key}}" \
  --output json
```

### Method 2: Azure AD Authentication (Recommended)

```bash
# Assign Storage Blob Data Contributor role
az role assignment create \
  --assignee "{{user-or-sp-id}}" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.Storage/storageAccounts/{{account}}"
```

### Method 3: SAS Token (Time-limited Access)

```bash
# Generate SAS token
az storage account generate-sas \
  --account-name "{{storage_account}}" \
  --permissions rwdl \
  --services b \
  --resource-types sco \
  --expiry "{{expiry-date}}" \
  --output tsv

# Use SAS token
az storage blob list \
  --account-name "{{storage_account}}" \
  --sas-token "{{sas_token}}" \
  --container-name "{{container}}"
```

## Python SDK Usage

### Authenticate and Create Client

```python
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

# Using Azure AD (recommended)
credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(
    account_url="https://{{account}}.blob.core.windows.net",
    credential=credential
)

# Using account key
from azure.storage.blob import BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(
    "DefaultEndpointsProtocol=https;AccountName={{account}};AccountKey={{key}};EndpointSuffix=core.windows.net"
)
```

### Container Operations

```python
# Create container
container_client = blob_service_client.create_container("{{container_name}}")

# List containers
containers = blob_service_client.list_containers()
for container in containers:
    print(container.name)

# Get container client
container_client = blob_service_client.get_container_client("{{container_name}}")
```

### Blob Operations

```python
# Upload blob
blob_client = blob_service_client.get_blob_client(container="{{container}}", blob="{{blob_name}}")
with open("{{local_file}}", "rb") as data:
    blob_client.upload_blob(data)

# Download blob
with open("{{download_path}}", "wb") as download_file:
    download_file.write(blob_client.download_blob().readall())

# List blobs
blobs = container_client.list_blobs()
for blob in blobs:
    print(blob.name)

# Delete blob
blob_client.delete_blob()
```

## AzCopy Usage (Large Transfers)

### Upload Files

```bash
# Upload single file
azcopy copy "{{local_file}}" "https://{{account}}.blob.core.windows.net/{{container}}/{{blob}}?{{sas_token}}"

# Upload directory
azcopy copy "{{local_dir}}" "https://{{account}}.blob.core.windows.net/{{container}}?{{sas_token}}" --recursive

# Upload with sync (mirror)
azcopy sync "{{local_dir}}" "https://{{account}}.blob.core.windows.net/{{container}}?{{sas_token}}" --recursive
```

### Download Files

```bash
# Download single file
azcopy copy "https://{{account}}.blob.core.windows.net/{{container}}/{{blob}}?{{sas_token}}" "{{local_path}}"

# Download container
azcopy copy "https://{{account}}.blob.core.windows.net/{{container}}?{{sas_token}}" "{{local_dir}}" --recursive
```

### Copy Between Containers

```bash
# Copy between storage accounts
azcopy copy "https://{{source_account}}.blob.core.windows.net/{{container}}?{{sas_token}}" "https://{{dest_account}}.blob.core.windows.net/{{container}}?{{sas_token}}" --recursive
```

## RBAC Roles for Blob Storage

| Role | Permissions |
|------|-------------|
| **Storage Blob Data Owner** | Full access (read, write, delete) |
| **Storage Blob Data Contributor** | Read, write, delete blobs |
| **Storage Blob Data Reader** | Read-only access |
| **Storage Blob Delegator** | Generate SAS tokens |

```bash
# Assign role
az role assignment create \
  --assignee "{{user-or-sp-id}}" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.Storage/storageAccounts/{{account}}"
```

## Soft Delete Configuration

```bash
# Enable soft delete (blob retention)
az storage account blob-service-properties update \
  --account-name "{{account}}" \
  --resource-group "{{rg}}" \
  --enable-delete-retention true \
  --delete-retention-days 14 \
  --output json

# Enable container soft delete
az storage account blob-service-properties update \
  --account-name "{{account}}" \
  --resource-group "{{rg}}" \
  --enable-container-delete-retention true \
  --container-delete-retention-days 14
```

## Lifecycle Management Setup

```bash
# Create lifecycle policy (JSON file)
az storage account management-policy create \
  --account-name "{{account}}" \
  --resource-group "{{rg}}" \
  --policy "{{policy_json}}" \
  --output json
```

Policy JSON example:
```json
{
  "rules": [
    {
      "name": "archive-old-blobs",
      "enabled": true,
      "type": "Lifecycle",
      "definition": {
        "filters": {
          "blobTypes": ["blockBlob"],
          "prefixMatch": ["logs/"]
        },
        "actions": {
          "baseBlob": {
            "tierToArchive": {"daysAfterModificationGreaterThan": 90},
            "delete": {"daysAfterModificationGreaterThan": 365}
          }
        }
      }
    }
  ]
}
```

## Static Website Setup

```bash
# Enable static website
az storage blob service-properties update \
  --account-name "{{account}}" \
  --static-website true \
  --index-document index.html \
  --error-document 404.html \
  --output json

# Upload website files to $web container
az storage blob upload \
  --account-name "{{account}}" \
  --container-name "$web" \
  --name index.html \
  --file index.html

# Get website URL
az storage account show --name "{{account}}" --query "primaryEndpoints.web"
```

## Common Azure Regions for Storage

| Region Code | Display Name |
|-------------|--------------|
| eastus | East US |
| eastus2 | East US 2 |
| westus | West US |
| westus2 | West US 2 |
| centralus | Central US |
| northeurope | North Europe |
| westeurope | West Europe |
| southeastasia | Southeast Asia |
| eastasia | East Asia |

## Quick Reference Commands

```bash
# Discover: `az account list-locations --query "[].name" -o tsv`; SKU list at `az storage account list-skus --output json`
# Create storage account
az storage account create --name {{user.storage_account_name}} --resource-group {{user.resource_group}} --location {{user.location}} --sku {{user.storage_sku}} --kind StorageV2

# Create container
az storage container create --name {{user.container_name}} --account-name {{user.storage_account_name}} --auth-mode login

# Upload blob
az storage blob upload --account-name {{user.storage_account_name}} --container-name {{user.container_name}} --name {{user.blob_name}} --file {{user.source_file}}

# Download blob
az storage blob download --account-name {{user.storage_account_name}} --container-name {{user.container_name}} --name {{user.blob_name}} --file {{user.dest_file}}

# List blobs
az storage blob list --account-name {{user.storage_account_name}} --container-name {{user.container_name}} --output json

# Delete blob
az storage blob delete --account-name {{user.storage_account_name}} --container-name {{user.container_name}} --name {{user.blob_name}}

# Delete storage account
az storage account delete --name {{user.storage_account_name}} --resource-group {{user.resource_group}} --yes
```