# Queue Storage Commands Reference

## Pre-flight (must run once before any operation)

```bash
# Get storage account key (used for all data-plane operations)
ACCOUNT_KEY=$(az storage account keys list --account-name "{{user.storage_account_name}}" --resource-group "{{user.resource_group}}" --query "[0].value" -o tsv)
```

## Queue Lifecycle Operations

### Create Queue

```bash
az storage queue create --name "{{user.queue_name}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --output json
```

SDK fallback: `QueueServiceClient.create_queue("{{user.queue_name}}")`

### Show / List Queues

```bash
az storage queue list --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --output json
az storage queue show --name "{{user.queue_name}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --output json
```

### Delete Queue

**Safety Gate**: MUST obtain explicit user confirmation. Show queue, get message count for data-loss warning. User must type exact queue name.

```bash
az storage queue show --name "{{user.queue_name}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --output json
# After confirmation:
az storage queue delete --name "{{user.queue_name}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --output json
```

### Clear Queue

**Safety Gate**: MUST obtain explicit user confirmation. Show queue metadata + approximate message count first.

```bash
az storage queue show --name "{{user.queue_name}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --query "approximate_message_count" -o tsv
# After confirmation:
az storage message clear --queue-name "{{user.queue_name}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --output json
```

## Message Operations

### Enqueue Message

```bash
az storage message put --queue-name "{{user.queue_name}}" --content "{{user.message_text}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --visibility-timeout 0 --time-to-live {{user.ttl_seconds|604800}} --output json
```

SDK fallback: `QueueClient.send_message("{{user.message_text}}", time_to_live=604800)`

### Dequeue / Peek Message

```bash
# Peek (no dequeue)
az storage message peek --queue-name "{{user.queue_name}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --num-messages 5 --output json
# Dequeue
az storage message get --queue-name "{{user.queue_name}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --num-messages 5 --visibility-timeout 30 --output json
```

### Update / Delete Message

```bash
# Update visibility timeout
az storage message update --queue-name "{{user.queue_name}}" --message-id "{{user.message_id}}" --pop-receipt "{{user.pop_receipt}}" --visibility-timeout "{{user.visibility_timeout}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --output json
# Delete message
az storage message delete --queue-name "{{user.queue_name}}" --message-id "{{user.message_id}}" --pop-receipt "{{user.pop_receipt}}" --account-name "{{user.storage_account_name}}" --account-key "$ACCOUNT_KEY" --output json
```

## Recovery Table

| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| QueueNotFound | Verify queue name |
| QueueAlreadyExists | Use different name |
| QuotaExceeded | HALT |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |
