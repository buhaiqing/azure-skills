# Integration Setup (Azure Load Balancer Skills)

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

# Network management (required for Load Balancer skills)
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

| Skill | Required RBAC Role |
|-------|-------------------|
| azure-loadbalancer-ops | Network Contributor |
| azure-appgateway-ops | Network Contributor |
| azure-frontdoor-ops | CDN Profile Contributor |
| azure-trafficmanager-ops | Traffic Manager Contributor |
| azure-network-ops | Network Contributor |

## Verify Credentials

```bash
az account show --output json
```

## Project-based Setup (pyproject.toml)

```toml
[project]
name = "azure-loadbalance-ops"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "azure-identity>=1.10.0",
    "azure-mgmt-resource>=21.0.0",
    "azure-mgmt-network>=23.0.0",
]
```

## Common Azure Regions for Load Balancing

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
| japaneast | Japan East |

## Safety Rules

- **NEVER** commit `.env` files
- **NEVER** write credentials into Skill documents
- Generated Skills use `{{env.*}}` placeholders only