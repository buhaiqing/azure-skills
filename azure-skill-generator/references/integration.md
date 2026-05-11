# Integration Setup (Azure Skills)

## Quick Start with .env

The recommended way to manage Azure credentials is via `.env` file:

```bash
# One-time setup: copy .env.example → .env and generate config
python azure-skill-generator/scripts/setup_env.py

# Edit .env and fill in your Azure credentials
# Then re-render config files
python azure-skill-generator/scripts/setup_env.py --render
```

This generates `azure-skill-generator/config.yaml` with your actual credential values, and resolves `{{env.*}}` placeholders in template files.

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
# Or via PowerShell:
Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi; Start-Process msiexec.exe -ArgumentList '/I AzureCLI.msi /quiet' -Wait
```

### Install Azure SDK for Python

```bash
# Core packages
pip install azure-identity azure-mgmt-resource

# Service-specific packages
pip install azure-mgmt-compute    # Virtual Machines
pip install azure-mgmt-storage   # Storage Accounts
pip install azure-mgmt-network   # Virtual Networks
pip install azure-mgmt-web       # App Services
pip install azure-mgmt-containerinstance  # Container Instances
pip install azure-mgmt-containerservice   # AKS
pip install azure-mgmt-sql       # Azure SQL
pip install azure-mgmt-cosmosdb  # Cosmos DB
pip install azure-mgmt-keyvault  # Key Vault
pip install azure-mgmt-redis     # Azure Cache for Redis
pip install azure-mgmt-monitor   # Azure Monitor
```

### Verify Installation

```bash
az --version
python -c "from azure.identity import DefaultAzureCredential; print('Azure SDK OK')"
```

## Credential Configuration

### Method A: Service Principal (Recommended for Automation)

**Create Service Principal** (Azure Portal or CLI):
```bash
# Create Service Principal with Contributor role
az ad sp create-for-rbac \
  --name "my-automation-sp" \
  --role "Contributor" \
  --scopes "/subscriptions/{{subscription-id}}" \
  --output json
```

Output:
```json
{
  "appId": "{{AZURE_CLIENT_ID}}",
  "displayName": "my-automation-sp",
  "name": "...",
  "password": "{{AZURE_CLIENT_SECRET}}",
  "tenant": "{{AZURE_TENANT_ID}}"
}
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
# Interactive login
az login

# Login with specific subscription
az login --subscription "{{subscription-id}}"

# Verify
az account show --output json
```

### Method C: Managed Identity (Azure VM/Container)

No configuration needed - Azure automatically authenticates when running on Azure resources with Managed Identity enabled.

```bash
# Enable on VM (Portal or CLI)
az vm identity assign --name "{{vm-name}}" --resource-group "{{rg}}"

# SDK auto-detects Managed Identity via DefaultAzureCredential
```

## Credential Priority Order

| Priority | Source | Used By |
|----------|--------|---------|
| 1 | Environment vars (SP) | CLI + SDK |
| 2 | `az login` session | CLI |
| 3 | Managed Identity | SDK (when on Azure) |
| 4 | VS Code login | SDK |

## Verify Credentials

```bash
# Check current account
az account show --output json
```

Expected output:
```json
{
  "environmentName": "AzureCloud",
  "id": "{{subscription-id}}",
  "isDefault": true,
  "name": "My Subscription",
  "state": "Enabled",
  "tenantId": "{{tenant-id}}",
  "user": {
    "name": "{{app-id}}",
    "type": "servicePrincipal"
  }
}
```

## Project-based Setup (pyproject.toml)

```toml
[project]
name = "azure-ops"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "azure-identity>=1.10.0",
    "azure-mgmt-resource>=21.0.0",
    "azure-mgmt-compute>=27.0.0",
    "azure-mgmt-storage>=20.0.0",
    "azure-mgmt-network>=23.0.0",
]

[tool.uv]
python-version = "3.10"
```

Sync command:
```bash
uv sync
source .venv/bin/activate
```

## Multi-cloud Credential Separation

```bash
# Azure - use AZURE_* prefix (standard)
export AZURE_SUBSCRIPTION_ID=...
export AZURE_TENANT_ID=...
export AZURE_CLIENT_ID=...
export AZURE_CLIENT_SECRET=...

# AWS - use AWS_* prefix (standard)
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1

# JD Cloud - use JDC_* prefix
export JDC_ACCESS_KEY=...
export JDC_SECRET_KEY=...
export JDC_REGION=cn-north-1

# Aliyun - use ALIYUN_* prefix
export ALIYUN_ACCESS_KEY_ID=...
export ALIYUN_ACCESS_KEY_SECRET=...
export ALIYUN_REGION=cn-hangzhou
```

## Safety Rules

- **NEVER** commit `.env` files (already in `.gitignore`)
- **NEVER** write credentials into Skill documents
- Generated Skills use `{{env.*}}` placeholders only
- Service Principal secrets should be rotated regularly

## Common Azure Regions

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
| japanwest | Japan West |
| australiaeast | Australia East |
| australiasoutheast | Australia Southeast |
| brazilsouth | Brazil South |
| canadacentral | Canada Central |
| canadaeast | Canada East |
| uksouth | UK South |
| ukwest | UK West |
| francecentral | France Central |
| francesouth | France South |
| switzerlandnorth | Switzerland North |
| switzerlandwest | Switzerland West |
| germanywestcentral | Germany West Central |
| norwayeast | Norway East |
| norwaywest | Norway West |
| swedencentral | Sweden Central |

List all regions:
```bash
az account list-locations --output json
```