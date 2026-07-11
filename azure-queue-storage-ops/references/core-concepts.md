# Azure Queue Storage Core Concepts

## What is Azure Queue Storage

- **Purpose**: Scalable message queue for asynchronous communication between application components
- **Category**: Storage / Messaging
- **Portal**: https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.Storage%2FstorageAccounts
- **Docs**: https://docs.microsoft.com/azure/storage/queues/
- **Pricing**: https://azure.microsoft.com/pricing/details/storage/queues/

## Primary Resources

| Resource | Description |
|----------|-------------|
| Storage Account | Top-level storage container (must be general-purpose v2) |
| Queue | Container for messages (within a storage account) |
| Message | Individual message (up to 64 KB, base64-encoded) |

## Architecture & Limits

### Resource ID Format
```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{account-name}/queueServices/default/queues/{queue-name}
```

### Queue Limits

| Limit | Value | Adjustable |
|-------|-------|------------|
| Max queue size | Unlimited (account max 500 TB) | No |
| Max queue name length | 3-63 characters | No |
| Max message size | 64 KB | No |
| Max messages per queue | Unlimited | No |
| Max TTL | 7 days (default) | Configurable |
| Min TTL | 1 second | Configurable |
| Default message TTL | 7 days (604800 seconds) | Configurable |
| Max visibility timeout | 7 days | Configurable |
| Default visibility timeout | 30 seconds | Configurable |
| Max dequeued messages per call | 32 | No |
| Max peeked messages per call | 32 | No |

### Naming Constraints

| Resource | Rules |
|----------|-------|
| Storage Account | 3-24 chars, lowercase alphanumeric only |
| Queue | 3-63 chars, lowercase alphanumeric and hyphens; must start/end with alphanumeric; no consecutive hyphens |

### Endpoint URL Format

```
https://{account-name}.queue.core.windows.net/{queue-name}
```

## Message Lifecycle

### Message States

1. **Active** — Message is in the queue and visible
2. **Invisible** — Message has been dequeued and is hidden (visibility timeout period)
3. **Expired** — TTL exceeded; message deleted automatically
4. **Deleted** — Explicitly deleted by consumer

### Enqueue → Dequeue → Process → Delete Flow

```
┌─────────┐    enqueue    ┌─────────┐   dequeue    ┌────────────┐   delete    ┌──────────┐
│ Producer │ ──────────→ │  Queue  │ ──────────→ │  Consumer  │ ──────────→ │ Removed  │
└─────────┘              └─────────┘              └────────────┘             └──────────┘
                                                       │
                                                       │ update visibility timeout
                                                       ▼
                                                 ┌────────────┐
                                                 │  Re-process │
                                                 └────────────┘
```

### Visibility Timeout

- When a message is dequeued, it becomes invisible to other consumers
- Default visibility timeout: 30 seconds
- Consumer can extend the timeout by calling `update_message`
- If consumer fails to delete before timeout expires, message becomes visible again (reappears)

### Message TTL (Time-to-Live)

- Default: 7 days (604800 seconds)
- Maximum: 7 days
- Minimum: 1 second
- After TTL expires, message is automatically deleted

## Poison Messages

### What is a Poison Message

A message that cannot be processed successfully by the consumer and keeps reappearing after the visibility timeout expires. Common causes:
- Malformed message content
- Missing dependencies referenced in the message
- Transient errors that never resolve

### Detection

- Track `dequeue_count` (number of times message has been dequeued)
- If dequeue_count exceeds a threshold (e.g., 5), treat as poison
- `az storage message get` returns `dequeue_count` field

### Handling Strategies

1. **Dead-letter queue**: Move poison messages to a separate queue for manual inspection
2. **Auto-delete**: Delete messages exceeding max dequeue count
3. **Log and alert**: Record poison message details for operational review

## SAS (Shared Access Signature)

### Types

| Type | Scope | Duration |
|------|-------|----------|
| Account-level SAS | All queues in storage account | Up to max expiry |
| Service-level SAS | Specific queue | Time-limited |

### Common Permissions for Queue Operations

| Permission | Letter | Operation |
|------------|--------|-----------|
| Read | r | Peek, list messages |
| Add | a | Enqueue message |
| Update | u | Update message |
| Process | p | Dequeue, delete messages |

## Storage Account Requirements

Queue Storage requires a **general-purpose v2 (StorageV2)** or **general-purpose v1 (Storage)** storage account. It is not available with BlobStorage or BlockBlobStorage account types.

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| Resource Group | Yes | `azure-resource-ops` |
| Storage Account | Yes | `azure-blobstorage-ops` |
| Virtual Network | No | `azure-network-ops` |
| Private Endpoint | No | `azure-network-ops` |

## Best Practices

### Performance
- Use batch operations (up to 32 messages per call) for bulk processing
- Keep message size small (< 64 KB) to reduce latency
- Use appropriate visibility timeout based on processing time
- Implement exponential backoff for retries

### Reliability
- Implement poison message handling
- Set appropriate TTL based on message criticality
- Use idempotent message processing (messages may be processed more than once)
- Log message IDs and pop receipts for traceability

### Security
- Use Azure AD authentication over account keys where possible
- Use SAS tokens for time-limited access
- Never log account keys or connection strings
- Validate and sanitize message content before processing

## Pricing Model

- **Pricing type**: Storage cost + transaction cost + data transfer
- **Key dimensions**: Queue storage size, number of operations, data transfer, replication
- **Free tier**: Limited free storage in Azure Free Account
- **Estimator**: https://azure.microsoft.com/pricing/calculator/
