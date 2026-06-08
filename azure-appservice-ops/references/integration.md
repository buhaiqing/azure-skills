# Integration Setup — Azure App Service

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
pip install azure-identity azure-mgmt-web azure-mgmt-resource
```

### Verify Installation

```bash
az --version
python -c "from azure.identity import DefaultAzureCredential; from azure.mgmt.web import WebSiteManagementClient; print('OK')"
```

## Credential Configuration

### Service Principal

```bash
az ad sp create-for-rbac \
  --name "my-appservice-automation-sp" \
  --role "Website Contributor" \
  --scopes "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --output json
```

Use environment variables; never write real values into skill files:

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
| Web App and plan create/update/delete | Website Contributor or Contributor |
| App settings update | Website Contributor or Contributor |
| Log and diagnostics read | Reader + Website Contributor for log config changes |
| VNet integration | Website Contributor + Network Contributor on subnet |
| Managed identity assignment | Managed Identity Operator or Contributor as required |

## Pre-flight Commands

```bash
az account show --output json
az group show --name "{{user.resource_group}}" --output json
az account list-locations --output json
az webapp list --resource-group "{{user.resource_group}}" --output json
az appservice plan list --resource-group "{{user.resource_group}}" --output json
```

## SDK Client

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.web import WebSiteManagementClient
import os

client = WebSiteManagementClient(
    DefaultAzureCredential(),
    subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
)
```

## Runtime Discovery

```bash
az webapp list-runtimes --linux --output json
az webapp list-runtimes --output json
```

## Safety Rules

- Use `{{env.*}}` placeholders for credentials only.
- Use `{{user.*}}` placeholders for app names, plan names, runtime, SKU, and settings keys.
- Treat publishing profiles, connection strings, and secret-like app settings as sensitive.
- Record full resource IDs in traces, masking secrets.
- Use Azure term **Location**, not region.
