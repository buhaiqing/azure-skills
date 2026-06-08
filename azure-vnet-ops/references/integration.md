# Integration Setup — Azure Virtual Network

## Environment Setup

Azure CLI and Azure SDK require authentication via Azure AD. Use Service Principal credentials through environment variables for automation.

### Install Azure CLI

```bash
# macOS
brew install azure-cli

# Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Install Azure SDK for Python

```bash
pip install azure-identity azure-mgmt-network azure-mgmt-resource
```

### Verify Installation

```bash
az --version
python -c "from azure.identity import DefaultAzureCredential; from azure.mgmt.network import NetworkManagementClient; print('OK')"
```

## Credential Configuration

### Service Principal

```bash
az ad sp create-for-rbac \
  --name "my-vnet-automation-sp" \
  --role "Network Contributor" \
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
| VNet/subnet create/update/delete | Network Contributor |
| Peering create/update/delete | Network Contributor on both VNets |
| Read-only inventory | Reader |
| Activity Log troubleshooting | Reader or Monitoring Reader |

## Pre-flight Commands

```bash
az account show --output json
az group show --name "{{user.resource_group}}" --output json
az account list-locations --output json
az network vnet list --output json
```

## SDK Client

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient
import os

client = NetworkManagementClient(
    DefaultAzureCredential(),
    subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
)
```

## Safety Rules

- Use `{{env.*}}` placeholders for credentials only.
- Ask for `{{user.resource_group}}`, `{{user.location}}`, and resource names once; reuse them.
- Record full resource IDs in traces, masking secrets.
- Use Azure term **Location**, not region.
