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

Azure Blob Storage is Microsoft's object storage solution for the cloud, optimized for storing massive amounts of unstructured data (text/binary data, images, videos, documents). This skill is an operational runbook with explicit scope, credential rules, dual-path execution (Azure CLI + Azure SDK), validation, and recovery.

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

Credential sources (the 4 `{{env.AZURE_*}}` vars above + auth priority) are a common skeleton — see [azure-cli-conventions.md § Credential Sources Priority Order](../../azure-skill-generator/references/azure-cli-conventions.md#credential-sources-priority-order). Business placeholders only:

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure Location (e.g., eastus) |
| `{{user.storage_account_name}}` | User input | Storage account name (3-24 chars, lowercase alphanumeric) |
| `{{user.container_name}}` | User input | Container name |
| `{{user.blob_name}}` | User input | Blob/file name |
| `{{user.local_file_path}}` | User input | Local source file for upload |
| `{{user.local_destination_path}}` | User input | Local target for download |
| `{{output.storage_account_id}}` | Last API response | Parse: `.id` from Azure CLI output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

The 5-step Pre-flight table and the CLI-retry-then-SDK fallback rule are common skeletons — see [azure-cli-conventions.md](../../azure-skill-generator/references/azure-cli-conventions.md). Full commands and SDK fallback for every operation live in [integration.md](references/integration.md).

## Operations

Each operation below shows the primary Azure CLI entry point. Full command variants, validation, recovery tables, and the Azure SDK for Python fallback are in [integration.md](references/integration.md).

### Create Storage Account
```bash
az storage account create --name "{{user.storage_account_name}}" --resource-group "{{user.resource_group}}" --location "{{user.location}}" --sku Standard_LRS --kind StorageV2 --access-tier Hot --allow-blob-public-access false --output json
```

### Create Blob Container
```bash
az storage container create --name "{{user.container_name}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --public-access off --output json
```

### Upload Blob
```bash
az storage blob upload --account-name "{{user.storage_account_name}}" --container-name "{{user.container_name}}" --name "{{user.blob_name}}" --file "{{user.local_file_path}}" --type block --output json
```

### Download Blob
```bash
az storage blob download --account-name "{{user.storage_account_name}}" --container-name "{{user.container_name}}" --name "{{user.blob_name}}" --file "{{user.local_destination_path}}" --output json
```

### List Blobs
```bash
az storage blob list --account-name "{{user.storage_account_name}}" --container-name "{{user.container_name}}" --output json
```

### Delete Blob

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

```bash
az storage blob delete --account-name "{{user.storage_account_name}}" --container-name "{{user.container_name}}" --name "{{user.blob_name}}" --output json
```

### Delete Storage Account

**Safety Gate**: MUST obtain explicit user confirmation before deletion. All data will be permanently lost.

```bash
az storage account delete --name "{{user.storage_account_name}}" --resource-group "{{user.resource_group}}" --yes --output json
```

## Account Key Security

Storage account data-plane commands use `--account-key` (or SAS token) for authentication. Never print the key value into logs or GCL traces — mask as `***`. Prefer Azure AD auth (`Storage Blob Data Contributor`) over shared keys where possible.

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

### Account Key Security (GCL scanning)
Storage account commands use `--account-key` for authentication. The GCL trace MUST NOT contain the account key value. The Critic scans for base64-encoded key strings in output. If detected, safety=0 → ABORT, regardless of operation success.

## Reference Files

- [Core Concepts](references/core-concepts.md) — account types, SKU/replication, access tiers, blob types
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md) — full CLI commands, SDK fallback, SAS, AzCopy
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Blob Storage Documentation](https://docs.microsoft.com/azure/storage/blobs/)
- [Azure CLI Storage Reference](https://docs.microsoft.com/cli/azure/storage)
- [Azure SDK Storage Module](https://docs.microsoft.com/python/api/azure-storage-blob/)
