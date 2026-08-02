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

## Full `az monitor` Command Reference

All operations follow dual-path: **Azure CLI (primary)** + **Azure SDK for Python (fallback)**. CLI failures retry up to 3× before falling back.

### 1. Metrics

```bash
# List available metrics for a resource
az monitor metrics list --resource "{{user.target_resource_id}}" --output json

# Get specific metric values
az monitor metrics list --resource "{{user.target_resource_id}}" \
  --metric "Percentage CPU" \
  --interval PT1M \
  --aggregation Average \
  --start-time "2026-05-10T00:00:00Z" \
  --end-time "2026-05-10T01:00:00Z" \
  --output json
```

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.monitor import MonitorManagementClient
import os

client = MonitorManagementClient(DefaultAzureCredential(), os.environ.get('AZURE_SUBSCRIPTION_ID'))
# client bootstrap: see ../../../azure-skill-generator/references/azure-sdk-usage.md#common-client-bootstrap

# Get metric definitions
definitions = client.metrics.list(
    resource_uri='{{user.target_resource_id}}'
)

# Get metric values
metrics = client.metrics.list(
    resource_uri='{{user.target_resource_id}}',
    metricnames='Percentage CPU',
    aggregation='Average',
    interval='PT1M'
)
```

### 2. Action Groups

```bash
# Create action group for alert notifications
az monitor action-group create \
  --name "{{user.action_group_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "Global" \
  --short-name "myaction" \
  --output json

# Add email notification
az monitor action-group create \
  --name "{{user.action_group_name}}" \
  --resource-group "{{user.resource_group}}" \
  --short-name "myaction" \
  --action-email name "email-action" email-address "admin@example.com" \
  --output json

# Add webhook notification
az monitor action-group create \
  --name "{{user.action_group_name}}" \
  --resource-group "{{user.resource_group}}" \
  --short-name "myaction" \
  --action-webhook name "webhook-action" webhook-uri "https://example.com/webhook" \
  --output json
```

### 3. Metric Alert Rule

```bash
az monitor metrics alert create \
  --name "{{user.alert_rule_name}}" \
  --resource-group "{{user.resource_group}}" \
  --scopes "{{user.target_resource_id}}" \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action "{{user.action_group_name}}" \
  --description "CPU usage exceeds 80%" \
  --output json
```

### 4. Log Alert Rule (Scheduled Query)

```bash
az monitor scheduled-query create \
  --name "{{user.alert_rule_name}}" \
  --resource-group "{{user.resource_group}}" \
  --scopes "{{user.log_analytics_workspace_id}}" \
  --condition-query "AzureActivity | where OperationName == 'RestartVM'" \
  --condition-threshold 1 \
  --evaluation-frequency 5m \
  --window-size 15m \
  --action "{{user.action_group_name}}" \
  --description "VM restart detected" \
  --output json
```

### 5. Log Analytics Query

```bash
# Execute KQL query in Log Analytics workspace
az monitor log-analytics query \
  --workspace "{{user.workspace_id}}" \
  --analytics-query "AzureActivity | take 10" \
  --timespan "1d" \
  --output json

# Query specific logs
az monitor log-analytics query \
  --workspace "{{user.workspace_id}}" \
  --analytics-query "Syslog | where TimeGenerated > ago(1h) | count" \
  --output json
```

```python
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient

credential = DefaultAzureCredential()
client = LogsQueryClient(credential)

# Execute KQL query
response = client.query_workspace(
    workspace_id='{{user.workspace_id}}',
    query='AzureActivity | take 10',
    timespan='1d'
)

# Access results
for table in response.tables:
    for row in table.rows:
        print(row)
```

### 6. Diagnostic Settings

```bash
az monitor diagnostic-settings create \
  --name "{{user.diagnostic_setting_name}}" \
  --resource "{{user.target_resource_id}}" \
  --workspace "{{user.workspace_id}}" \
  --logs "[{category:'Administrative',enabled:true},{category:'Security',enabled:true}]" \
  --metrics "[{category:'AllMetrics',enabled:true,timegrain:'PT1M'}]" \
  --output json
```

### 7. Activity Log

```bash
# List recent activity log events
az monitor activity-log list \
  --caller "{{user.caller}}" \
  --start-time "2026-05-09T00:00:00Z" \
  --end-time "2026-05-10T00:00:00Z" \
  --output json

# Query by resource
az monitor activity-log list \
  --resource "{{user.target_resource_id}}" \
  --output json

# Query by event name
az monitor activity-log list \
  --event-name "RestartVM" \
  --output json
```

### 8. Delete Operations (Destructive — require confirmation)

```bash
# Show alert rule before deletion
az monitor metrics alert show --name "{{user.alert_rule_name}}" --resource-group "{{user.resource_group}}" --output json
# Then, after explicit user confirmation (exact rule name typed):
az monitor metrics alert delete --name "{{user.alert_rule_name}}" --resource-group "{{user.resource_group}}" --output json

# Delete action group (after confirming no rules reference it)
az monitor action-group delete --name "{{user.action_group_name}}" --resource-group "{{user.resource_group}}" --output json
```