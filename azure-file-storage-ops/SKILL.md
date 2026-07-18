---
name: azure-file-storage-ops
description: >-
  Use when operating Azure File Storage (SMB/NFS file shares) via Azure CLI or Azure SDK;
  user mentions "Azure Files", "File Share", "SMB share", "NFS share", or file storage operations.
license: MIT
compatibility: Azure CLI 2.0+, Azure SDK (Python 3.10+), valid Azure credentials.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-07-11"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure File Storage Operations Skill

## Overview

Azure Files offers managed cloud file shares supporting SMB and NFS protocols.
This is the slim entrypoint (~100-150 lines): triggers, scope, flow, safety gates, and links.
Detailed commands, SDK snippets, and design detail live in `references/`.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure Files", "File Share", "SMB share", "NFS share"
- Task involves CRUD on **File Shares** (create, show, update, list, delete, snapshot)
- Keywords: file share, SMB, NFS, share snapshot, soft-delete, quota, mount
- Mounting/unmounting file shares to/from VMs or on-premises

### SHOULD NOT Use When
- Blob/Container operations → delegate to: `azure-blobstorage-ops`
- Storage Account management (create/delete account) → delegate to: `azure-blobstorage-ops`
- AD/Domain Join → delegate to: `azure-audit-ops`
- Monitoring/Alerts → delegate to: `azure-monitor-ops`
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
| `{{user.storage_account_name}}` | User input | 3-24 chars, lowercase alphanumeric |
| `{{user.share_name}}` | User input | 3-63 chars, lowercase + hyphens |
| `{{user.quota_gb}}` | User input | GB (1-5120 standard, 100-102400 premium; default 100) |
| `{{output.share_id}}` | Last API response | Parse: `.id` from CLI output |
| `{{user.prefix}}` | User input | Prefix filter for list operations |
| `{{output.deleted_share_version}}` | Last API response | Parse from `az storage share list --include-deleted` |

## Execution Flow

Every operation: **Pre-flight → Execute → Validate → Recover**. Detailed commands and SDK in `references/`.

### Pre-flight (shared)
| Check | Method | On Failure |
|-------|--------|------------|
| CLI | `az --version` | Install CLI 2.0+ |
| Credentials | `az account show` | HALT; configure env |
| Subscription | `az account list -o json` | Suggest valid sub |
| RG | `az group show -n {{user.resource_group}}` | Create or suggest |
| Storage Account | `az storage account show -n {{user.storage_account_name}} -g {{user.resource_group}}` | Delegate to `azure-blobstorage-ops` |

### Operations (CREATE / SHOW / LIST / UPDATE / SNAPSHOT)

Full CLI commands and SDK fallbacks: see [references/integration.md](references/integration.md). Summary:

| Op | Key Params |
|----|-------------|
| CREATE | `--quota {{user.quota_gb}}`; NFS: `--protocol NFS` |
| SHOW | `--account-name` + `--account-key` (fetched from `az storage account keys list`) |
| LIST | optional `--prefix "{{user.prefix}}"` |
| UPDATE | `--quota {{user.quota_gb}}` |
| SNAPSHOT | no extra params |

Validate via `az storage share show -n {{user.share_name}} ...` — expect `status: active`.

### Operation: Soft-Delete / Undelete Share

- CLI list deleted: see [integration.md](references/integration.md)
- SDK restore: `client.file_shares.restore(...)` with `deleted_share_version` — full snippet in [integration.md](references/integration.md)
- CLI has no native undelete; SDK required.

### Operation: Delete File Share

**Safety Gate**: MUST obtain explicit user confirmation. All data and snapshots permanently lost.

```bash
# Show share + list snapshots (data-loss warning)
az storage share show -n "{{user.share_name}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" -o json
az storage share list --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --include-snapshots -o json
# After user confirms exact share name:
az storage share delete -n "{{user.share_name}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --delete-snapshots include -o json
```

### Recover Table

| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| ShareAlreadyExists | Use different name |
| QuotaExceeded | HALT; request increase |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |

Full error table: [references/troubleshooting.md](references/troubleshooting.md).

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** (see `AGENTS.md §3–§8`).

| Parameter | Value |
|-----------|-------|
| GCL | **required**, max_iter=2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE share → **required**; Safety=0 → ABORT
- CREATE share → **required**; quota defaults enforced
- SNAPSHOT → **required**
- UPDATE quota → recommended
- LIST / SHOW (read-only) → recommended

### Account Key Security
Account key MUST be fetched via `-o tsv` into a shell variable and NEVER echoed. Critic scans for base64-encoded keys in trace. If detected, safety=0 → ABORT.

## Reference Files

- [Core Concepts](references/core-concepts.md) — SMB/NFS, quotas, snapshots, soft-delete, sync
- [Troubleshooting](references/troubleshooting.md) — mount failures, auth, quota, sync conflicts
- [Integration Setup](references/integration.md) — credentials, CLI/SDK setup, AzCopy
- [Rubric](references/rubric.md) — GCL scoring dimensions
- [Prompt Templates](references/prompt-templates.md) — Generator + Critic prompts

