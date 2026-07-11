# Integration Setup (Azure Queue Storage)

## Environment Setup

Azure Queue Storage operations require Azure CLI and Azure SDK.

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

# Queue-specific package
pip install azure-storage-queue

# Verify
python -c "from azure.storage.queue import QueueServiceClient; print('Azure Queue SDK OK')"
```

## Credential Configuration

### Method A: Service Principal (Recommended for Automation)

```bash
# Create Service Principal
az ad sp create-for-rbac \
  --name "my-queue-automation-sp" \
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

# Use key in queue operations
az storage queue list \
  --account-name "{{storage_account}}" \
  --account-key "{{key}}" \
  --output json
```

### Method 2: Azure AD Authentication (Recommended)

```bash
# Assign Storage Queue Data Contributor role
az role assignment create \
  --assignee "{{user-or-sp-id}}" \
  --role "Storage Queue Data Contributor" \
  --scope "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.Storage/storageAccounts/{{account}}"
```

### Method 3: SAS Token (Time-limited Access)

```bash
# Generate SAS token for queue
az storage account generate-sas \
  --account-name "{{storage_account}}" \
  --permissions raup \
  --services q \
  --resource-types sco \
  --expiry "{{expiry-date}}" \
  --output tsv

# Use SAS token
az storage queue list \
  --account-name "{{storage_account}}" \
  --sas-token "{{sas_token}}" \
  --output json
```

## Python SDK Usage

### Authenticate and Create Client

```python
from azure.identity import DefaultAzureCredential
from azure.storage.queue import QueueServiceClient

# Using Azure AD (recommended)
credential = DefaultAzureCredential()
queue_service = QueueServiceClient(
    account_url="https://{{account}}.queue.core.windows.net",
    credential=credential
)

# Using connection string
from azure.storage.queue import QueueServiceClient
queue_service = QueueServiceClient.from_connection_string(
    "DefaultEndpointsProtocol=https;AccountName={{account}};AccountKey={{key}};EndpointSuffix=core.windows.net"
)
```

### Queue Operations

```python
# Create queue
queue_service.create_queue("{{queue_name}}")

# List queues
queues = queue_service.list_queues()
for q in queues:
    print(q.name)

# Get queue client
queue_client = queue_service.get_queue_client("{{queue_name}}")

# Delete queue
queue_client.delete_queue()
```

### Message Operations

```python
# Send message
queue_client.send_message("{{message_content}}")

# Send message with custom TTL
queue_client.send_message("{{message_content}}", time_to_live=3600)

# Peek messages (without dequeuing)
peeked_messages = queue_client.peek_messages(max_messages=5)
for msg in peeked_messages:
    print(msg.content, msg.inserted_on)

# Receive messages (dequeue)
messages = queue_client.receive_messages(max_messages=5, visibility_timeout=60)
for msg in messages:
    print(msg.content, msg.dequeue_count)
    # Process message...
    queue_client.delete_message(msg)

# Update message visibility timeout
queue_client.update_message(
    message,  # Received message object
    pop_receipt=message.pop_receipt,
    visibility_timeout=120  # Extend processing window
)

# Clear all messages
queue_client.clear_messages()
```

## RBAC Roles for Queue Storage

| Role | Permissions |
|------|-------------|
| **Storage Queue Data Contributor** | Read, write, delete queues and messages |
| **Storage Queue Data Reader** | Read-only access (peek, list) |
| **Storage Queue Data Message Processor** | Peek, retrieve, and delete messages |
| **Storage Queue Data Message Sender** | Send messages only |

```bash
# Assign role
az role assignment create \
  --assignee "{{user-or-sp-id}}" \
  --role "Storage Queue Data Contributor" \
  --scope "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.Storage/storageAccounts/{{account}}"
```

## Soft Delete for Queue Storage

Queue Storage supports soft delete for queues (not individual messages).

```bash
# Enable queue soft delete
az storage account queue-service-properties update \
  --account-name "{{account}}" \
  --resource-group "{{rg}}" \
  --enable-queue-delete-retention true \
  --queue-delete-retention-days 14 \
  --output json
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
# Create queue
az storage queue create --name myqueue --account-name mySA

# List queues
az storage queue list --account-name mySA

# Show queue
az storage queue show --name myqueue --account-name mySA

# Enqueue message
az storage message put --queue-name myqueue --content "Hello" --account-name mySA

# Peek messages
az storage message peek --queue-name myqueue --account-name mySA --num-messages 5

# Dequeue messages
az storage message get --queue-name myqueue --account-name mySA --num-messages 5 --visibility-timeout 30

# Update message
az storage message update --queue-name myqueue --message-id "id" --pop-receipt "receipt" --visibility-timeout 60 --account-name mySA

# Delete message
az storage message delete --queue-name myqueue --message-id "id" --pop-receipt "receipt" --account-name mySA

# Clear queue
az storage message clear --queue-name myqueue --account-name mySA

# Delete queue
az storage queue delete --name myqueue --account-name mySA
```
