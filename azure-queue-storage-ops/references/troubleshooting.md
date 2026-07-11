# Azure Queue Storage Troubleshooting Guide

## Common API Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| InvalidParameter | 400 | Request validation failed | Fix args per Azure REST API docs |
| InvalidResourceName | 400 | Queue name invalid | Fix naming convention (3-63 chars, lowercase) |
| QueueNotFound | 404 | Queue does not exist | Verify queue name |
| QueueAlreadyExists | 409 | Queue already exists | Use different name or check existing |
| MessageNotFound | 404 | Message not found (expired or deleted) | Verify message ID and pop receipt |
| AuthenticationFailed | 403 | Invalid credentials or permissions | Check keys/SAS/Azure AD |
| AuthorizationFailed | 403 | RBAC permission insufficient | Add required role |
| AccessDenied | 403 | Access policy denies operation | Check queue access policy |
| QuotaExceeded | 400/402 | Storage limit reached | HALT; request quota increase |
| ServiceQuotaExceededException | 400 | Request rate exceeded | Retry with exponential backoff |
| ThrottlingException | 429 | Rate limit exceeded | Backoff, retry 3x |
| InternalError | 500 | Azure service error | Retry 3x; HALT with correlation ID |
| ServiceUnavailable | 503 | Service temporarily down | Retry 3x; HALT |
| OperationTimedOut | 500 | Operation timeout | Retry with smaller batch size |

## Diagnostic Order

### Storage Account Issues

1. **Verify credentials**: `az account show`
2. **Verify subscription**: Check `AZURE_SUBSCRIPTION_ID`
3. **Verify resource group**: `az group show --name {{rg}}`
4. **Get storage account**: `az storage account show --name {{account}} --resource-group {{rg}}`
5. **Check account kind**: Must be StorageV2 or Storage (Queue Storage not available on BlobStorage-only accounts)
6. **List account keys**: `az storage account keys list --account-name {{account}}`
7. **Test queue operations**: Try list queues

### Queue Issues

1. **List queues**: `az storage queue list --account-name {{account}}`
2. **Show queue**: `az storage queue show --name {{queue}} --account-name {{account}}`
3. **Check queue metadata**: Review approximate message count and metadata
4. **Check queue access policy**: `az storage queue policy list --queue-name {{queue}} --account-name {{account}}`

### Message Issues

1. **Peek messages**: `az storage message peek --queue-name {{queue}} --account-name {{account}}`
2. **Check dequeue count**: Review `dequeue_count` field (high count = poison message)
3. **Verify message ID and pop receipt**: Most message operations require both
4. **Check message TTL**: Messages expire after TTL; re-enqueue if needed

## Queue Creation Issues

### Issue: Queue name invalid

**Symptoms**:
- Error: "InvalidResourceName"
- Name contains invalid characters

**Resolution**:
- Name must be 3-63 characters
- Only lowercase letters, numbers, and hyphens
- Must start and end with alphanumeric
- No consecutive hyphens

### Issue: Storage account type incompatible

**Symptoms**:
- Queue operations fail on BlobStorage-only accounts

**Resolution**:
```bash
# Check account kind
az storage account show --name {{account}} --query "kind"

# Must be StorageV2 or Storage (general purpose)
# Create a general-purpose v2 account if needed
az storage account create --name {{new_account}} --resource-group {{rg}} --location eastus --sku Standard_LRS --kind StorageV2
```

## Authentication Issues

### Issue: Authentication failed

**Symptoms**:
- Operations fail with "AuthenticationFailed"
- Cannot access queue

**Diagnosis Steps**:
1. Verify account keys: `az storage account keys list --account-name {{account}}`
2. Check if keys were rotated
3. Verify SAS token validity
4. Check Azure AD permissions (requires Storage Queue Data Contributor role)

**Resolution Options**:
| Cause | Resolution |
|-------|------------|
| Invalid account key | Get fresh key: `az storage account keys list` |
| Expired SAS token | Generate new SAS token |
| Azure AD permission missing | Add Storage Queue Data Contributor role |

### Issue: Access denied

**Symptoms**:
- "AccessDenied" or "AuthorizationFailed"
- Cannot enqueue/dequeue messages

**Resolution**:
```bash
# Check Azure AD RBAC assignment
az role assignment list --assignee {{user-id}} --output json

# Add required role
az role assignment create \
  --assignee {{user-id}} \
  --role "Storage Queue Data Contributor" \
  --scope "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.Storage/storageAccounts/{{account}}"
```

## Message Processing Issues

### Issue: Message keeps reappearing (poison message)

**Symptoms**:
- Message dequeue_count keeps increasing
- Same message processed repeatedly
- Consumer cannot delete successfully

**Diagnosis**:
```bash
# Check dequeue count
az storage message peek --queue-name {{queue}} --account-name {{account}}
# Look for dequeue_count field > threshold (e.g., 5)
```

**Resolution**:
1. Move poison messages to a dead-letter queue
2. Inspect message content for malformation
3. Fix processing logic
4. If unrecoverable, delete the poison message

### Issue: Message not visible after dequeuing

**Symptoms**:
- Message disappears but consumer hasn't processed it
- Cannot find the message

**Diagnosis**:
1. Check visibility timeout value (message is hidden during timeout)
2. Wait for visibility timeout to expire (message reappears)
3. Check if another consumer already processed and deleted it

**Resolution**:
```bash
# Wait for visibility timeout to expire
# Or if consumer failed, message will reappear automatically
# Check approximate message count
az storage queue show --name {{queue}} --query "approximate_message_count"
```

### Issue: Cannot delete message

**Symptoms**:
- Delete operation fails
- Message ID and pop receipt mismatch

**Resolution**:
```bash
# Pop receipt changes after each visibility timeout; get fresh ones
az storage message get --queue-name {{queue}} --account-name {{account}} --num-messages 1 --visibility-timeout 30

# Use the new message_id and pop_receipt
az storage message delete \
  --queue-name {{queue}} \
  --message-id {{new_message_id}} \
  --pop-receipt {{new_pop_receipt}} \
  --account-name {{account}}
```

### Issue: Message too large

**Symptoms**:
- Enqueue fails with size error
- Message exceeds 64 KB limit

**Resolution**:
```bash
# Check message size
# Max message size is 64 KB (base64-encoded)
# For larger payloads:
# 1. Store payload in Blob Storage
# 2. Enqueue a reference message with blob URL + SAS token
```

### Issue: Message expired

**Symptoms**:
- Message disappears before processing
- MessageNotFound on operations

**Resolution**:
```bash
# Set longer TTL when enqueuing (max 7 days)
az storage message put \
  --queue-name {{queue}} \
  --content "{{message}}" \
  --account-name {{account}} \
  --time-to-live 604800
```

## Performance Issues

### Issue: Slow enqueue/dequeue

**Symptoms**:
- High latency in queue operations
- Throughput is low

**Resolution Options**:
- Use batch operations (up to 32 messages per `receive_messages`)
- Use Premium storage account for high performance
- Check network bandwidth
- Consider using Service Bus for high-throughput messaging scenarios

## Queue Cleanup Issues

### Issue: Cannot delete non-empty queue

**Symptoms**:
- Queue delete operation requires explicit confirmation
- Data loss concern

**Resolution**:
- Always show queue metadata before deletion
- Confirm approximate message count
- Obtain exact queue name confirmation from user

## Activity Log for Debugging

```bash
# Check queue operations
az monitor activity-log list \
  --resource "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.Storage/storageAccounts/{{account}}" \
  --output json
```

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Data loss | Critical | Immediate Azure support ticket |
| Production queue inaccessible | Critical | Immediate support ticket |
| Security breach indicator | Critical | Immediate support + security review |
| Persistent authentication issues | High | Support ticket with error details |
| Quota/capacity issues | Medium | Quota increase request via portal |
| Performance degradation | Medium | Performance analysis + support |
| Feature clarification | Low | Azure forums or documentation |
