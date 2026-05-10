# Integration Setup (Azure Traffic Manager Skills)

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

# Traffic Manager management
pip install azure-mgmt-trafficmanager
```

### Verify Installation

```bash
az --version
python -c "from azure.identity import DefaultAzureCredential; from azure.mgmt.trafficmanager import TrafficManagerManagementClient; print('OK')"
```

## Credential Configuration

### Method A: Service Principal (Recommended for Automation)

**Create Service Principal**:
```bash
az ad sp create-for-rbac \
  --name "my-automation-sp" \
  --role "Traffic Manager Contributor" \
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
| Create Traffic Manager profile | Traffic Manager Contributor |
| Manage endpoints | Traffic Manager Contributor |
| Configure routing methods | Traffic Manager Contributor |

## Traffic Manager DNS Naming

Traffic Manager DNS names must be **globally unique**:
- Becomes: `{{dns-name}}.trafficmanager.net`
- Cannot conflict with any existing profile
- Use descriptive names with organization prefix

## Verify Credentials

```bash
az account show --output json
```

## Project-based Setup (pyproject.toml)

```toml
[project]
name = "azure-trafficmanager-ops"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "azure-identity>=1.10.0",
    "azure-mgmt-resource>=21.0.0",
    "azure-mgmt-trafficmanager>=1.0.0",
]
```

## Safety Rules

- **NEVER** commit `.env` files
- **NEVER** write credentials into Skill documents
- Generated Skills use `{{env.*}}` placeholders only
- Traffic Manager DNS names must be globally unique