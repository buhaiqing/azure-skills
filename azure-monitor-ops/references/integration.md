# Integration Setup (Azure Monitor Skills)

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

# Monitor management
pip install azure-mgmt-monitor

# Log Analytics query client
pip install azure-monitor-query
```

### Verify Installation

```bash
az --version
python -c "from azure.identity import DefaultAzureCredential; from azure.mgmt.monitor import MonitorManagementClient; from azure.monitor.query import LogsQueryClient; print('OK')"
```

## Credential Configuration

### Method A: Service Principal (Recommended for Automation)

**Create Service Principal**:
```bash
az ad sp create-for-rbac \
  --name "my-automation-sp" \
  --role "Monitoring Contributor" \
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
| Read metrics | Monitoring Reader |
| Create alerts | Monitoring Contributor |
| Query logs | Log Analytics Reader |
| Configure diagnostic settings | Monitoring Contributor |
| Create Log Analytics workspace | Contributor + Monitoring Contributor |

## Resource ID Format

Azure Monitor requires full resource IDs for most operations:

```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/{provider}/{type}/{name}
```

Examples:
```
# VM
/subscriptions/abc123/resourceGroups/my-rg/providers/Microsoft.Compute/virtualMachines/my-vm

# Storage Account
/subscriptions/abc123/resourceGroups/my-rg/providers/Microsoft.Storage/storageAccounts/my-storage

# Log Analytics Workspace
/subscriptions/abc123/resourceGroups/my-rg/providers/Microsoft.OperationalInsights/workspaces/my-workspace

# Application Insights
/subscriptions/abc123/resourceGroups/my-rg/providers/Microsoft.Insights/components/my-appinsights
```

## Get Resource ID

```bash
# Get resource ID for any Azure resource
az resource show --name "{{resource_name}}" --resource-group "{{rg}}" --resource-type "{{provider/type}}" --query id -o tsv

# Example: Get VM resource ID
az vm show --name my-vm --resource-group my-rg --query id -o tsv
```

## Verify Credentials

```bash
az account show --output json
```

## Project-based Setup (pyproject.toml)

```toml
[project]
name = "azure-monitor-ops"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "azure-identity>=1.10.0",
    "azure-mgmt-resource>=21.0.0",
    "azure-mgmt-monitor>=5.0.0",
    "azure-monitor-query>=1.0.0",
]
```

## KQL Query Examples

```kql
// Recent Azure Activity
AzureActivity | take 10

// VM restarts in last 24 hours
AzureActivity | where TimeGenerated > ago(24h) | where OperationName == 'RestartVM'

// Top error events
Event | where EventLevelName == 'Error' | count by Source

// Performance metrics
Perf | where ObjectName == 'Processor' | where CounterName == '% Processor Time' | avg(CounterValue)

// Application requests
AppRequests | where Success == false | count by AppRoleName
```

## Common Metric Namespaces

| Resource Type | Namespace |
|--------------|-----------|
| VM | `Microsoft.Compute/virtualMachines` |
| Storage | `Microsoft.Storage/storageAccounts` |
| SQL Database | `Microsoft.Sql/servers/databases` |
| Web App | `Microsoft.Web/sites` |
| Load Balancer | `Microsoft.Network/loadBalancers` |
| Key Vault | `Microsoft.KeyVault/vaults` |
| App Insights | `Microsoft.Insights/components` |

## Safety Rules

- **NEVER** commit `.env` files
- **NEVER** write credentials into Skill documents
- Generated Skills use `{{env.*}}` placeholders only
- Alert thresholds should be validated against baseline metrics
- Action groups should be tested before production use