# Integration Setup — Azure DNS

## Environment Setup

Azure CLI and Azure SDK require authentication via Azure AD. Use Service Principal credentials through environment variables for automation.

> SDK 方法名经实测校验: `azure-mgmt-dns==9.0.0` — `DnsManagementClient.zones` 下: `begin_delete`, `create_or_update`, `get`, `list`, `list_by_resource_group`, `update`；`DnsManagementClient.record_sets` 下: `create_or_update`, `delete`, `get`, `list_all_by_dns_zone`, `list_by_dns_zone`, `list_by_type`, `update`。
> `azure-mgmt-privatedns==1.2.0` — `PrivateDnsManagementClient.private_zones` 下: `begin_create_or_update`, `begin_delete`, `begin_update`, `get`, `list`, `list_by_resource_group`；`record_sets` 下: `create_or_update`, `delete`, `get`, `list`, `list_by_type`, `update`；`virtual_network_links` 下: `begin_create_or_update`, `begin_delete`, `begin_update`, `get`, `list`。

### Install Azure CLI

```bash
# macOS
brew install azure-cli

# Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Install Azure SDK for Python

```bash
pip install azure-identity azure-mgmt-dns azure-mgmt-resource
```

For private DNS zones, also install:
```bash
pip install azure-mgmt-privatedns
```

### Verify Installation

```bash
az --version
python -c "from azure.identity import DefaultAzureCredential; from azure.mgmt.dns import DnsManagementClient; print('OK')"
```

## Credential Configuration

### Service Principal

```bash
az ad sp create-for-rbac \
  --name "my-dns-automation-sp" \
  --role "DNS Zone Contributor" \
  --scopes "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --output json
```

Store values as environment variables; never write real values into skill files:

```bash
export AZURE_SUBSCRIPTION_ID="{{env.AZURE_SUBSCRIPTION_ID}}"
export AZURE_TENANT_ID="{{env.AZURE_TENANT_ID}}"
export AZURE_CLIENT_ID="{{env.AZURE_CLIENT_ID}}"
export AZURE_CLIENT_SECRET="{{env.AZURE_CLIENT_SECRET}}"
```

### Interactive Login

```bash
az login
az account set --subscription "{{env.AZURE_SUBSCRIPTION_ID}}"
az account show --output json
```

## Required RBAC

| Operation | Required role |
|-----------|---------------|
| DNS zone create/update/delete | DNS Zone Contributor |
| Record set create/update/delete | DNS Zone Contributor |
| Private DNS zone create/update/delete | DNS Zone Contributor |
| Private DNS VNet link create/delete | DNS Zone Contributor on zone + Network Contributor on VNet |
| Read-only inventory | Reader or DNS Zone Reader |
| Activity Log troubleshooting | Reader or Monitoring Reader |

## Pre-flight Commands

```bash
az account show --output json
az group show --name "{{user.resource_group}}" --output json
az network dns zone list --output json
```

## SDK Client

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.dns import DnsManagementClient
import os

client = DnsManagementClient(
    credential=DefaultAzureCredential(),
    subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
)

# Verify subscription access
try:
    zones = client.zones.list()
    print("Connected to Azure DNS management client")
except Exception as e:
    raise RuntimeError(f"Credential verification failed: {e}")
```

### Private DNS SDK Client

```python
from azure.mgmt.privatedns import PrivateDnsManagementClient

private_client = PrivateDnsManagementClient(
    credential=DefaultAzureCredential(),
    subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
)
```

## Safety Rules

- Use `{{env.*}}` placeholders for credentials only.
- Ask for `{{user.resource_group}}`, `{{user.zone_name}}`, `{{user.record_set_name}}`, and `{{user.record_type}}` once; reuse them.
- Record full resource IDs in traces, masking secrets.
- Zone names are globally unique in Azure DNS — validate availability before creation.
- Private DNS zones require VNet link registration before they become resolvable.
