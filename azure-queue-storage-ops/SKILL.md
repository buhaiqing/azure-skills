---
name: azure-queue-storage-ops
description: >-
  Use when operating Azure Queue Storage resources via Azure CLI or Azure SDK;
  user mentions "Queue Storage", "Azure Queue", "Storage Queue", or queue message operations.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints and storage accounts.
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

# Azure Queue Storage Operations Skill

## Overview

Azure Queue Storage is a service for storing large numbers of messages (up to 64 KB each) accessible via authenticated HTTP/HTTPS calls. This skill manages queues and queue messages.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure Queue Storage", "Storage Queue", "Queue message"
- Task involves CRUD on **Storage Queues** or **Queue Messages** (create, list, enqueue, dequeue, peek, update, delete, clear)
- Keywords: queue, message, enqueue, dequeue, peek, visibility timeout, poison message

### SHOULD NOT Use When
- Service Bus queues (brokered messaging) → delegate to: `azure-servicebus-ops`
- Event Hubs (event ingestion) → delegate to: `azure-eventhub-ops`
- Blob Storage → delegate to: `azure-blobstorage-ops`
- Billing only → delegate to: `azure-cost-ops`
- VNet / Private Endpoint configuration → delegate to: `azure-vnet-ops`
- Resource Group management → delegate to: `azure-resourcegroup-ops`

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
| `{{user.queue_name}}` | User input | 3-63 chars, lowercase, hyphens allowed |
| `{{user.message_text}}` | User input | Message content (base64-encoded, max 64 KB) |
| `{{user.message_id}}` | User input | Message ID from dequeue response |
| `{{user.pop_receipt}}` | User input | Pop receipt from dequeue response |
| `{{user.ttl_seconds}}` | User input | Message TTL in seconds (default 604800 = 7 days) |
| `{{output.*}}` | Last API response | Parse per Azure REST API docs |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**.

### Pre-flight Checks
1. CLI available: `az --version`
2. Credentials valid: `az account show --output json`
3. Subscription valid: `az account set --subscription "{{env.AZURE_SUBSCRIPTION_ID}}"`
4. Resource Group exists: `az group show --name "{{user.resource_group}}"`
5. Storage Account exists: `az storage account show --name "{{user.storage_account_name}}" --resource-group "{{user.resource_group}}"`
6. Queue endpoint available: `az storage account show --name "{{user.storage_account_name}}" --query "primaryEndpoints.queue"`
7. Get account key (required for data-plane operations):
   ```bash
   ACCOUNT_KEY=$(az storage account keys list --account-name "{{user.storage_account_name}}" --resource-group "{{user.resource_group}}" --query "[0].value" -o tsv)
   ```
   All subsequent commands assume `$ACCOUNT_KEY` is set.

### Operations (CLI)

See [commands.md](references/commands.md) for full command reference:

| Operation | Safety Gate | Key Flag |
|-----------|-------------|----------|
| Create Queue | — | `--account-key "$ACCOUNT_KEY"` |
| List / Show Queue | — | `--account-key "$ACCOUNT_KEY"` |
| Enqueue Message | — | `--time-to-live {{user.ttl_seconds\|604800}}` |
| Dequeue / Peek Message | — | `--visibility-timeout 30` |
| Update / Delete Message | — | `--message-id` + `--pop-receipt` |
| Clear Queue | **REQUIRED** | Confirm + show message count first |
| Delete Queue | **REQUIRED** | Confirm + user types exact queue name |

SDK fallback paths: `QueueServiceClient` (queue lifecycle), `QueueClient` (message ops).

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate. See `AGENTS.md §3–§8`.

| Parameter | Value |
|-----------|-------|
| GCL | **required** |
| max_iterations | 2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE queue → **required**; Safety=0 → ABORT
- CLEAR queue → **required**; data-loss warning + Safety=0 → ABORT
- DELETE message → **required**; pop-receipt verification
- CREATE queue / ENQUEUE message → **required**
- LIST / SHOW / PEEK (read-only) → recommended

### Account Key Security

Queue storage commands use `--account-key` for authentication. The GCL trace MUST NOT contain the account key value. If detected, safety=0 → ABORT.

## L4 Auto-Feedback Loop

For autonomous operation on non-risky operations, wrap skill execution with the L4 auto-feedback loop:

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-queue-storage-ops \
  --operation queue_create \
  --command "az storage queue create --name {{user.queue_name}} --account-name {{user.account_name}} ..." \
  --desired-state '{"name": "{{user.queue_name}}"}' \
  [--dry-run] [--trace-id <uuid>]
```

- **Non-risky operations** (queue_create): auto-feedback loop active
- **Risky operations** (delete): always bypass loop and require explicit human confirmation
- Healing policy: see [`scripts/self_healing/queue-storage_heal.json`](../../scripts/self_healing/queue-storage_heal.json)
- Findings written to `.runtime/findings/` on escalation (CADL auto-trigger)

## Reference Files

- [Core Concepts](references/core-concepts.md) — architecture, limits, message lifecycle, poison messages
- [Commands](references/commands.md) — detailed CLI commands, SDK fallbacks, recovery table
- [Troubleshooting](references/troubleshooting.md) — error codes, diagnostics, poison handling
- [Integration Setup](references/integration.md) — credentials, SDK usage, RBAC, quick reference
- [Rubric](references/rubric.md) — GCL scoring dimensions
- [Prompt Templates](references/prompt-templates.md) — G/C prompt templates

## See Also

- [Azure Queue Storage Documentation](https://docs.microsoft.com/azure/storage/queues/)
- [Azure CLI Storage Queue Reference](https://docs.microsoft.com/cli/azure/storage/queue)
- [Azure SDK Queue Module](https://docs.microsoft.com/python/api/azure-storage-queue/)


> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
