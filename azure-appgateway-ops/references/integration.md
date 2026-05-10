# Integration Setup (Azure Application Gateway Skills)

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

# Network management (required for Application Gateway skills)
pip install azure-mgmt-network
```

### Verify Installation

```bash
az --version
python -c "from azure.identity import DefaultAzureCredential; from azure.mgmt.network import NetworkManagementClient; print('OK')"
```

## Credential Configuration

### Method A: Service Principal (Recommended for Automation)

**Create Service Principal**:
```bash
az ad sp create-for-rbac \
  --name "my-automation-sp" \
  --role "Network Contributor" \
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
| Create Application Gateway | Network Contributor |
| Configure WAF | Network Contributor + WAF Policy Contributor |
| Manage SSL Certificates | Network Contributor |

## Application Gateway Prerequisites

### 1. Dedicated Subnet

Application Gateway requires a **dedicated subnet**:
- Minimum 32 IP addresses
- Not shared with other resources
- Subnet must exist before creating AGW

```bash
# Create VNet with dedicated AGW subnet
az network vnet create \
  --name "my-vnet" \
  --resource-group "{{rg}}" \
  --location "{{location}}" \
  --subnet-name "agw-subnet" \
  --subnet-prefix "10.0.1.0/26"  # At least 32 IPs
```

### 2. Public IP (for public Application Gateway)

```bash
# Create Public IP for AGW
az network public-ip create \
  --name "agw-pip" \
  --resource-group "{{rg}}" \
  --location "{{location}}" \
  --sku Standard \
  --output json
```

## Verify Credentials

```bash
az account show --output json
```

## Project-based Setup (pyproject.toml)

```toml
[project]
name = "azure-appgateway-ops"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "azure-identity>=1.10.0",
    "azure-mgmt-resource>=21.0.0",
    "azure-mgmt-network>=23.0.0",
]
```

## Safety Rules

- **NEVER** commit `.env` files
- **NEVER** write credentials into Skill documents
- Generated Skills use `{{env.*}}` placeholders only
- SSL certificate passwords use `{{env.*}}` placeholders