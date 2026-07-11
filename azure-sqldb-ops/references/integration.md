# Azure SQL Database Integration and Commands

## Required Tools

```bash
az version --output json
az account show --output json
az provider show --namespace Microsoft.Sql --output json
```

If `Microsoft.Sql` is not registered, HALT and ask for approval before registration:

```bash
az provider register --namespace Microsoft.Sql --output json
```

## Required RBAC

| Operation | Minimum Role |
|-----------|--------------|
| Read/show/list/metrics | Reader + Monitoring Reader |
| Create/update/start/stop/delete server or DB | Contributor or SQL DB Contributor |
| Elastic pool management | Contributor on server scope |
| Firewall rule management | Contributor on server scope |
| Private networking changes | Network Contributor on network scope + server permissions |
| Role assignment changes | User Access Administrator or Owner; prefer delegate to `azure-audit-ops` |

Do not ask for database passwords/connection strings. If connectivity checks require DB auth, instruct the user to run client-side commands (e.g. `sqlcmd`/`sqlalchemy`) with their own secret source.

## Pre-flight Checklist

```bash
az account show --output json
az group show --name "{{user.resource_group}}" --output json
az account list-locations --query "[?name=='{{user.location}}']" --output json
az provider show --namespace Microsoft.Sql --query "registrationState" --output json
```

For existing server:

```bash
az sql server show \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

For metric names:

```bash
az monitor metrics list-definitions \
  --resource "{{output.server_id}}" \
  --output json
```

## Azure CLI Primary Path

### List and Show

```bash
az sql server list \
  --resource-group "{{user.resource_group}}" \
  --output json

az sql server show \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az sql db list \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az sql db show \
  --name "{{user.database_name}}" \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### Create Logical Server

```bash
az sql server create \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --admin-user "{{user.admin_login}}" \
  --output json
```

Avoid embedding admin passwords in skill content. Use Azure CLI secure prompting or a secret manager outside this repository. Validate:

```bash
az sql server show \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,state:state,fqdn:fullyQualifiedDomainName,version:version}" \
  --output json
```

### Create Database

```bash
# DTU model
az sql db create \
  --name "{{user.database_name}}" \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --service-objective "{{user.service_objective}}" \
  --output json

# vCore model (General Purpose)
az sql db create \
  --name "{{user.database_name}}" \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --edition GeneralPurpose \
  --family Gen5 \
  --capacity "{{user.vcore_count}}" \
  --output json
```

### Scale Database (compute / Max Size)

```bash
# Change service objective (compute tier)
az sql db update \
  --name "{{user.database_name}}" \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --service-objective "{{user.service_objective}}" \
  --output json

# Change Max Size (safe to grow; shrinking below used size is blocked)
az sql db update \
  --name "{{user.database_name}}" \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --max-size "{{user.max_size}}" \
  --output json
```

Scale down or parameter changes requiring restart need confirmation. `maxSizeBytes` cannot be lowered below current used data size.

### Elastic Pool

```bash
az sql elastic-pool create \
  --name "{{user.elastic_pool_name}}" \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --edition "{{user.pool_edition}}" \
  --capacity "{{user.pool_capacity}}" \
  --output json

az sql elastic-pool update \
  --name "{{user.elastic_pool_name}}" \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --capacity "{{user.pool_capacity}}" \
  --output json
```

Add a DB to a pool:

```bash
az sql db update \
  --name "{{user.database_name}}" \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --elastic-pool "{{user.elastic_pool_name}}" \
  --output json
```

### Start / Stop Server

```bash
az sql server stop \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az sql server start \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

Stop/start production requires explicit confirmation and client-impact statement.

### Firewall Rules

```bash
az sql server firewall-rule list \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az sql server firewall-rule create \
  --name "{{user.rule_name}}" \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --start-ip-address "{{user.start_ip}}" \
  --end-ip-address "{{user.end_ip}}" \
  --output json
```

Broad ranges such as `0.0.0.0`–`255.255.255.255` require refusal unless a documented emergency approval exists. Also consider toggling "Allow Azure services" only when needed:

```bash
az sql server update \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --set "publicNetworkAccess"="Enabled" \
  --output json
```

(Only adjust `publicNetworkAccess` when explicitly required; prefer private endpoints for production.)

### Delete

```bash
az sql db show \
  --name "{{user.database_name}}" \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# After explicit confirmation:
az sql db delete \
  --name "{{user.database_name}}" \
  --server "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --yes \
  --output json
```

Deleting the server removes all child DBs/pools (irreversible):

```bash
az sql server show \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# After explicit confirmation:
az sql server delete \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --yes \
  --output json
```

## Azure SDK Fallback

Use SDK only after CLI transient failures are retried up to 3x.

```python
import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.sql import SqlManagementClient

credential = DefaultAzureCredential()
client = SqlManagementClient(
    credential,
    subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
)

server = client.servers.get(
    resource_group_name="{{user.resource_group}}",
    server_name="{{user.server_name}}",
)
print(server.id)
```

Create/update database pattern:

```python
poller = client.databases.begin_create_or_update(
    resource_group_name="{{user.resource_group}}",
    server_name="{{user.server_name}}",
    database_name="{{user.database_name}}",
    parameters={
        "location": "{{user.location}}",
        "sku": {"name": "{{user.service_objective}}"},
        # vCore example: {"name": "GP_Gen5", "tier": "GeneralPurpose",
        #                "family": "Gen5", "capacity": 4}
    },
)
result = poller.result(timeout=2700)
print(result.id)
```

Scale (service objective / max size):

```python
poller = client.databases.begin_update(
    resource_group_name="{{user.resource_group}}",
    server_name="{{user.server_name}}",
    database_name="{{user.database_name}}",
    parameters={
        "sku": {"name": "{{user.service_objective}}"},
        # "max_size_bytes": <int>  # safe to grow only
    },
)
result = poller.result(timeout=2700)
print(result.id)
```

Delete pattern:

```python
poller = client.databases.begin_delete(
    resource_group_name="{{user.resource_group}}",
    server_name="{{user.server_name}}",
    database_name="{{user.database_name}}",
)
poller.result(timeout=2700)
```

## Polling

| Operation | Poll Interval | Max Wait |
|-----------|---------------|----------|
| create/update/scale/delete (DB/pool) | 30s | 45m |
| server start/stop | 30s | 30m |
| firewall rule update | 15s | 10m |

On timeout, do not repeat mutation. Re-read server/database state and report uncertainty.
