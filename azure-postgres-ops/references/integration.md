# Azure PostgreSQL Integration and Commands

## Required Tools

```bash
az version --output json
az account show --output json
az provider show --namespace Microsoft.DBforPostgreSQL --output json
```

If `Microsoft.DBforPostgreSQL` is not registered, HALT and ask for approval before registration:

```bash
az provider register --namespace Microsoft.DBforPostgreSQL --output json
```

## Required RBAC

| Operation | Minimum Role |
|-----------|--------------|
| Read/show/list/metrics | Reader + Monitoring Reader |
| Create/update/start/stop/restart/delete/restore | Contributor or PostgreSQL Flexible Server Contributor |
| Firewall rule management | Contributor on server scope |
| Private networking changes | Network Contributor on network scope + server permissions |
| Role assignment changes | User Access Administrator or Owner; prefer delegate to `azure-audit-ops` |

Do not ask for database passwords. If connectivity checks require DB auth, instruct the user to run client-side commands with their own secret source.

## Pre-flight Checklist

```bash
az account show --output json
az group show --name "{{user.resource_group}}" --output json
az account list-locations --query "[?name=='{{user.location}}']" --output json
az provider show --namespace Microsoft.DBforPostgreSQL --query "registrationState" --output json
```

For existing servers:

```bash
az postgres flexible-server show \
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
az postgres flexible-server list \
  --resource-group "{{user.resource_group}}" \
  --output json

az postgres flexible-server show \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### Create Flexible Server

```bash
az postgres flexible-server create \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --sku-name "{{user.sku_name}}" \
  --version "{{user.postgres_version}}" \
  --storage-size "{{user.storage_size_gb}}" \
  --backup-retention "{{user.backup_retention_days}}" \
  --output json
```

Avoid embedding admin passwords in skill content. Use Azure CLI secure prompts or environment/secret manager outside this repository.

Validate:

```bash
az postgres flexible-server show \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,state:state,fqdn:fullyQualifiedDomainName,sku:sku.name,version:version}" \
  --output json
```

### Start / Stop / Restart

```bash
az postgres flexible-server start \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az postgres flexible-server stop \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az postgres flexible-server restart \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

Stop/restart production requires explicit confirmation and client impact statement.

### Scale / Update

```bash
az postgres flexible-server update \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --sku-name "{{user.sku_name}}" \
  --storage-size "{{user.storage_size_gb}}" \
  --output json
```

Scale down or parameter changes requiring restart need confirmation.

### Firewall Rules

```bash
az postgres flexible-server firewall-rule list \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az postgres flexible-server firewall-rule create \
  --name "{{user.rule_name}}" \
  --server-name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --start-ip-address "{{user.start_ip}}" \
  --end-ip-address "{{user.end_ip}}" \
  --output json
```

Broad ranges such as `0.0.0.0-255.255.255.255` require refusal unless a documented emergency approval exists.

### Restore / PITR

```bash
az postgres flexible-server restore \
  --name "{{user.restore_server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --source-server "{{user.server_name}}" \
  --restore-time "{{user.restore_time}}" \
  --output json
```

Restore should create a separate target server unless the user provides an explicit approved cutover plan.

### Delete

```bash
az postgres flexible-server show \
  --name "{{user.server_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# After explicit confirmation:
az postgres flexible-server delete \
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
from azure.mgmt.rdbms.postgresql_flexibleservers import PostgreSQLManagementClient

credential = DefaultAzureCredential()
client = PostgreSQLManagementClient(
    credential,
    subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
)

server = client.servers.get(
    resource_group_name="{{user.resource_group}}",
    server_name="{{user.server_name}}",
)
print(server.id)
```

Create/update pattern:

```python
poller = client.servers.begin_create(
    resource_group_name="{{user.resource_group}}",
    server_name="{{user.server_name}}",
    parameters={
        "location": "{{user.location}}",
        "sku": {"name": "{{user.sku_name}}"},
        "version": "{{user.postgres_version}}",
        "storage": {"storage_size_gb": "{{user.storage_size_gb}}"},
        "backup": {"backup_retention_days": "{{user.backup_retention_days}}"},
    },
)
result = poller.result(timeout=2700)
print(result.id)
```

Delete pattern:

```python
poller = client.servers.begin_delete(
    resource_group_name="{{user.resource_group}}",
    server_name="{{user.server_name}}",
)
poller.result(timeout=2700)
```

## Polling

| Operation | Poll Interval | Max Wait |
|-----------|---------------|----------|
| create/update/scale/delete/restore | 30s | 45m |
| start/stop/restart | 30s | 30m |
| firewall rule update | 15s | 10m |

On timeout, do not repeat mutation. Re-read server state and report uncertainty.
