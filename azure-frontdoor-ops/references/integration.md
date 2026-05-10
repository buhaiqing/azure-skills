# Integration Setup (Azure Front Door Skills)

## Environment Setup

Azure CLI and Azure SDK require authentication via Azure AD. Use **Service Principal** for automation.

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

# CDN management (required for Front Door skills)
pip install azure-mgmt-cdn
```

### Verify Installation

```bash
az --version
python -c "from azure.identity import DefaultAzureCredential; from azure.mgmt.cdn import CdnManagementClient; print('OK')"
```

## Credential Configuration

### Method A: Service Principal (Recommended for Automation)

**Create Service Principal**:
```bash
az ad sp create-for-rbac \
  --name "my-automation-sp" \
  --role "CDN Profile Contributor" \
  --scopes "/subscriptions/{{subscription-id}}" \
  --output json
```

**Store credentials as environment variables**:
```bash
export AZURE_SUBSCRIPTION_ID="{{subscription-id}}"
export AZURE_TENANT_ID="{{tenant-id}}"
export AZURE_CLIENT_ID="{{app-id}}"
export AZURE_CLIENT_SECRET="{{password}}"
```

### Method B: Azure CLI Login (Interactive)

```bash
az login --subscription "{{subscription-id}}"
az account show --output json
```

## Required Permissions

| Operation | Required RBAC Role |
|-----------|-------------------|
| Create Front Door profile | CDN Profile Contributor |
| Manage endpoints | CDN Profile Contributor |
| Configure WAF (Premium) | CDN Profile Contributor + WAF Policy Contributor |
| Manage custom domains | CDN Profile Contributor |

## Front Door Endpoint Naming

Front Door endpoint names must be **globally unique**:
- Becomes part of DNS name: `{{endpoint-name}}-{{hash}}.azurefd.net`
- Cannot conflict with any existing Front Door endpoint
- Use descriptive names with organization prefix

## Verify Credentials

```bash
az account show --output json
```

## Project-based Setup (pyproject.toml)

```toml
[project]
name = "azure-frontdoor-ops"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "azure-identity>=1.10.0",
    "azure-mgmt-resource>=21.0.0",
    "azure-mgmt-cdn>=12.0.0",
]
```

## Safety Rules

- **NEVER** commit `.env` files
- **NEVER** write credentials into Skill documents
- Generated Skills use `{{env.*}}` placeholders only
- Front Door endpoint names must be globally unique