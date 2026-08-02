# Azure Cosmos DB Integration and Commands

## Required Tools

```bash
az version --output json
az account show --output json
az provider show --namespace Microsoft.DocumentDB --output json
```

If `Microsoft.DocumentDB` is not registered, HALT and ask for approval before registration:

```bash
az provider register --namespace Microsoft.DocumentDB --output json
```

## Required RBAC

| Operation | Minimum Role |
|-----------|--------------|
| Read/show/list/metrics | Reader + Monitoring Reader |
| Create/update/scale/region/consistency | Contributor or Cosmos DB Account Contributor |
| Key list/regenerate | Contributor on account scope (regenerate is disruptive) |
| Private networking changes | Network Contributor on network scope + account permissions; prefer delegate to `azure-privateendpoint-ops` |
| Role assignment changes | User Access Administrator or Owner; prefer delegate to `azure-audit-ops` |

Do not ask for account keys/connection strings. If connectivity checks require DB auth, instruct the user to run client-side commands with their own secret source.

## Pre-flight Checklist

```bash
az account show --output json
az group show --name "{{user.resource_group}}" --output json
az account list-locations --query "[?name=='{{user.location}}']" --output json
az provider show --namespace Microsoft.DocumentDB --query "registrationState" --output json
```

For existing accounts:

```bash
az cosmosdb show \
  --name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

For metric names:

```bash
az monitor metrics list-definitions \
  --resource "{{output.account_id}}" \
  --output json
```

## Azure CLI Primary Path

### List and Show Account

```bash
az cosmosdb list \
  --resource-group "{{user.resource_group}}" \
  --output json

az cosmosdb show \
  --name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### Create Account (SQL API)

```bash
az cosmosdb create \
  --name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --kind "GlobalDocumentDB" \
  --default-consistency-level "Session" \
  --output json
```

Validate:

```bash
az cosmosdb show \
  --name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,state:provisioningState,kind:kind,consistency:consistencyPolicy.defaultConsistencyLevel,locations:locations[].locationName}" \
  --output json
```

### SQL Database and Container

```bash
az cosmosdb sql database create \
  --account-name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --name "{{user.database_name}}" \
  --output json

az cosmosdb sql container create \
  --account-name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --database-name "{{user.database_name}}" \
  --name "{{user.container_name}}" \
  --partition-key-path "{{user.partition_key}}" \
  --throughput "{{user.throughput_rus}}" \
  --output json
```

Confirm the partition key path at create time — it cannot be changed without recreating the container.

### Scale RU/s (Manual)

```bash
az cosmosdb sql container throughput update \
  --account-name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --database-name "{{user.database_name}}" \
  --name "{{user.container_name}}" \
  --throughput "{{user.throughput_rus}}" \
  --output json
```

### Scale RU/s (Autoscale)

```bash
az cosmosdb sql container throughput update \
  --account-name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --database-name "{{user.database_name}}" \
  --name "{{user.container_name}}" \
  --max-throughput "{{user.max_throughput_rus}}" \
  --output json
```

Scale down or disabling autoscale on a hot workload needs confirmation.

### Keys and Connection Strings

Avoid embedding account keys/connection strings in skill content. Use environment/secret manager outside this repository.

```bash
az cosmosdb keys list \
  --name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az cosmosdb list-connection-strings \
  --name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

Regenerate keys after explicit confirmation only:

```bash
# After explicit confirmation:
az cosmosdb keys regenerate \
  --name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --key-kind "primary" \
  --output json
```

### Consistency and Global Distribution

```bash
az cosmosdb update \
  --name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --default-consistency-level "BoundedStaleness" \
  --output json

az cosmosdb region add \
  --name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --output json
```

Consistency changes and region add/remove in production require explicit confirmation.

### Delete Account and Container

```bash
az cosmosdb sql container delete \
  --account-name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --database-name "{{user.database_name}}" \
  --name "{{user.container_name}}" \
  --yes \
  --output json

az cosmosdb show \
  --name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# After explicit confirmation:
az cosmosdb delete \
  --name "{{user.account_name}}" \
  --resource-group "{{user.resource_group}}" \
  --yes \
  --output json
```

## Azure SDK Fallback

Use SDK only after CLI transient failures are retried up to 3x.

```python
import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.cosmosdb import CosmosDBManagementClient

client = CosmosDBManagementClient(DefaultAzureCredential(), os.environ["AZURE_SUBSCRIPTION_ID"])
# client bootstrap: see ../../../azure-skill-generator/references/azure-sdk-usage.md#common-client-bootstrap

account = client.database_accounts.get(
    resource_group_name="{{user.resource_group}}",
    account_name="{{user.account_name}}",
)
print(account.id)
```

Create/update pattern (control plane):

```python
poller = client.database_accounts.begin_create_or_update(
    resource_group_name="{{user.resource_group}}",
    account_name="{{user.account_name}}",
    create_update_parameters={
        "location": "{{user.location}}",
        "kind": "GlobalDocumentDB",
        "consistency_policy": {"default_consistency_level": "Session"},
        "locations": [{"location_name": "{{user.location}}"}],
    },
)
result = poller.result(timeout=2700)
print(result.id)
```

Data-plane RU/s / item operations use the `azure-cosmos` SDK package (not `azure-mgmt-cosmosdb`). Authenticate with a token credential (e.g. `DefaultAzureCredential`), never the Service Principal secret directly. 注：数据面示例在此，操作排障参考 [troubleshooting.md](troubleshooting.md)。

```python
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
# 注意：DefaultAzureCredential 需拥有 Cosmos DB 数据面权限（scope: https://cosmos.azure.com/.default）
client = CosmosClient(
    url="https://{{user.account_name}}.documents.azure.com:443/",
    credential=credential,
)
# Read container throughput (handle both manual and autoscale):
container = client.get_database_client("{{user.database_name}}").get_container_client("{{user.container_name}}")
offer = container.read_offer()
is_autoscale = "offerAutoscaleSettings" in offer.properties.get("content", {})
if is_autoscale:
    max_throughput = offer.properties["content"]["offerAutoscaleSettings"]["maxThroughput"]
    print(f"Autoscale max RU/s: {max_throughput}")
else:
    max_throughput = offer.offer_throughput
    print(f"Manual RU/s: {max_throughput}")
```

Delete pattern:

```python
poller = client.database_accounts.begin_delete(
    resource_group_name="{{user.resource_group}}",
    account_name="{{user.account_name}}",
)
poller.result(timeout=2700)
```

## Polling

| Operation | Poll Interval | Max Wait |
|-----------|---------------|----------|
| create/update account/region/consistency | 30s | 45m |
| container/database create/delete | 15s | 15m |
| throughput update | 15s | 10m |
| key regenerate | 15s | 10m |

On timeout, do not repeat mutation. Re-read state and report uncertainty.
