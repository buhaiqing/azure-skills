---
name: azure-blobstorage-ops
description: >-
  Use when operating Azure Blob Storage resources via Azure CLI or Azure SDK;
  user mentions "Blob Storage", "Azure Blob", "Storage Account", "Object Storage", or blob/container operations.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints and storage accounts.
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

# Azure Blob Storage Operations Skill

## Overview

Azure Blob Storage is Microsoft's object storage solution for the cloud, optimized for storing massive amounts of unstructured data (text/binary data, images, videos, documents). This skill is an operational runbook with explicit scope, credential rules, pre-flight checks, dual-path execution (Azure CLI + Azure SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure Blob Storage", "Blob", "Storage Account", "Object Storage"
- Task involves CRUD on **Storage Accounts** or **Blob Containers** (create, show, update, delete, list)
- Keywords: blob, container, storage account, object storage, block blob, append blob, page blob
- Uploading/downloading files to/from cloud storage
- Managing storage containers and blobs

### SHOULD NOT Use When
- File Shares (SMB) → delegate to: `azure-filestorage-ops`
- Table Storage → delegate to: `azure-tablestorage-ops`
- Queue Storage → delegate to: `azure-queuestorage-ops`
- Disk Storage (VM disks) → delegate to: `azure-disk-ops`
- Billing only → delegate to: `azure-cost-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure region (e.g., eastus) |
| `{{user.storage_account_name}}` | User input | Storage account name (3-24 chars, lowercase alphanumeric) |
| `{{user.container_name}}` | User input | Container name |
| `{{user.blob_name}}` | User input | Blob/file name |
| `{{output.storage_account_id}}` | Last API response | Parse: `.id` from Azure CLI output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create Storage Account

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show` | HALT; configure env |
| Subscription valid | `az account list --output json` | Suggest valid subscription |
| Resource Group exists | `az group show --name {{user.resource_group}}` | Create or suggest existing |
| Location valid | `az account list-locations --output json` | Suggest valid location |
| Name valid (3-24 chars, lowercase) | Validate name format | Fix naming convention |

#### Execute — Azure CLI (Primary)
```bash
# Create general-purpose v2 storage account (recommended)
az storage account create \
  --name "{{user.storage_account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --access-tier Hot \
  --allow-blob-public-access false \
  --output json

# Create with additional options
az storage account create \
  --name "{{user.storage_account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --sku Standard_GRS \
  --kind StorageV2 \
  --access-tier Hot \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false \
  --enable-hierarchical-namespace false \
  --output json
```

#### Execute — Azure SDK (Fallback)
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.storage import StorageManagementClient
import os

credential = DefaultAzureCredential()
client = StorageManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

# Create storage account
storage_account = client.storage_accounts.begin_create(
    resource_group_name='{{user.resource_group}}',
    account_name='{{user.storage_account_name}}',
    parameters={
        'location': '{{user.location}}',
        'sku': {'name': 'Standard_LRS'},
        'kind': 'StorageV2',
        'access_tier': 'Hot',
        'allow_blob_public_access': False
    }
).result()
```

#### Validate
```bash
# Verify storage account state
az storage account show \
  --name "{{user.storage_account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Check provisioning state: should be "Succeeded"
# Get account keys for further operations
az storage account keys list \
  --account-name "{{user.storage_account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| StorageAccountAlreadyExists | Use different name or check existing |
| QuotaExceeded | HALT; request quota increase |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |

### Operation: Create Blob Container

```bash
# Get storage account key first
ACCOUNT_KEY=$(az storage account keys list \
  --account-name "{{user.storage_account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "[0].value" -o tsv)

# Create container
az storage container create \
  --name "{{user.container_name}}" \
  --account-name "{{user.storage_account_name}}" \
  --account-key "$ACCOUNT_KEY" \
  --public-access off \
  --output json
```

### Operation: Upload Blob

```bash
# Upload file to container
az storage blob upload \
  --account-name "{{user.storage_account_name}}" \
  --container-name "{{user.container_name}}" \
  --name "{{user.blob_name}}" \
  --file "{{user.local_file_path}}" \
  --type block \
  --output json

# Upload with overwrite
az storage blob upload \
  --account-name "{{user.storage_account_name}}" \
  --container-name "{{user.container_name}}" \
  --name "{{user.blob_name}}" \
  --file "{{user.local_file_path}}" \
  --overwrite true \
  --output json
```

### Operation: Download Blob

```bash
# Download blob to local file
az storage blob download \
  --account-name "{{user.storage_account_name}}" \
  --container-name "{{user.container_name}}" \
  --name "{{user.blob_name}}" \
  --file "{{user.local_destination_path}}" \
  --output json
```

### Operation: List Blobs

```bash
# List all blobs in container
az storage blob list \
  --account-name "{{user.storage_account_name}}" \
  --container-name "{{user.container_name}}" \
  --output json

# List with prefix filter
az storage blob list \
  --account-name "{{user.storage_account_name}}" \
  --container-name "{{user.container_name}}" \
  --prefix "{{user.prefix}}" \
  --output json
```

### Operation: Delete Blob

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

```bash
# Show blob before deletion
az storage blob show \
  --account-name "{{user.storage_account_name}}" \
  --container-name "{{user.container_name}}" \
  --name "{{user.blob_name}}" \
  --output json

# Request confirmation
# Then proceed with deletion:
az storage blob delete \
  --account-name "{{user.storage_account_name}}" \
  --container-name "{{user.container_name}}" \
  --name "{{user.blob_name}}" \
  --output json
```

### Operation: Delete Storage Account

**Safety Gate**: MUST obtain explicit user confirmation before deletion. All data will be permanently lost.

```bash
# Show storage account before deletion
az storage account show \
  --name "{{user.storage_account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# List containers to warn about data loss
az storage container list \
  --account-name "{{user.storage_account_name}}" \
  --output json

# Request confirmation - user must type exact account name
# Then proceed with deletion:
az storage account delete \
  --name "{{user.storage_account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --yes \
  --output json
```

## Storage Account Types

| Kind | Description | Use Case |
|------|-------------|----------|
| **StorageV2** | General-purpose v2 (recommended) | Most scenarios, all features |
| **Storage** | General-purpose v1 (legacy) | Legacy systems |
| **BlobStorage** | Blob-only (legacy) | Blob-only scenarios |
| **BlockBlobStorage** | Premium block blob | High-performance blobs |
| **FileStorage** | Premium file shares | High-performance SMB |

## SKU Tiers

| SKU | Replication | Price | Use Case |
|-----|-------------|-------|----------|
| **Standard_LRS** | Local redundant | Lowest | Dev/test, non-critical |
| **Standard_ZRS** | Zone redundant | Medium | Production, HA within region |
| **Standard_GRS** | Geo redundant | Higher | Disaster recovery |
| **Standard_GZRS** | Geo + Zone redundant | Highest | Mission-critical |
| **Premium_LRS** | Premium local | High performance | High IOPS requirements |

## Access Tiers

| Tier | Description | Use Case |
|------|-------------|----------|
| **Hot** | Frequent access, higher storage cost | Active data |
| **Cool** | Infrequent access, lower storage cost | Backup, archives (30+ days) |
| **Cold** | Rarely accessed, lowest storage cost | Long-term backup (90+ days) |

## Blob Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Block Blob** | Blocks uploaded independently | Documents, images, videos |
| **Append Blob** | Append-only operations | Logs, audit trails |
| **Page Blob** | 512-byte pages | VHDs, random write |

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
- DELETE storage account (`az storage account delete`) → **required**; Safety=0 → ABORT
- DELETE container (`az storage container delete`) → **required**; data-loss warning + Safety=0 → ABORT
- DELETE blob (`az storage blob delete`) → **required**; exact name confirmation + Safety=0 → ABORT
- CREATE storage account → **required**; security defaults enforced (`--allow-blob-public-access false`)
- UPLOAD with overwrite → **required**; explicit `--overwrite true` consent
- LIST / SHOW / DOWNLOAD (read-only) → recommended

### Account Key Security

Storage account commands use `--account-key` for authentication. The GCL trace MUST NOT contain
the account key value. The Critic scans for base64-encoded key strings in output. If detected,
safety=0 → ABORT, regardless of operation success.

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Blob Storage Documentation](https://docs.microsoft.com/azure/storage/blobs/)
- [Azure CLI Storage Reference](https://docs.microsoft.com/cli/azure/storage)
- [Azure SDK Storage Module](https://docs.microsoft.com/python/api/azure-storage-blob/)
> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
