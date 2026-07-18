---
name: azure-monitor-ops
description: >-
  Use when operating Azure Monitor resources via Azure CLI or Azure SDK;
  user mentions "Monitor", "Metrics", "Alerts", "Log Analytics", "Application Insights",
  "Activity Log", or monitoring/alerting scenarios.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints.
metadata:
  author: azure
  version: "1.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Monitor Operations Skill

## Overview

Azure Monitor provides comprehensive monitoring, diagnostics, and alerting for Azure resources and applications. This skill is an operational runbook with explicit scope, credential rules, pre-flight checks, dual-path execution (Azure CLI + Azure SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "Azure Monitor", "Metrics", "Alerts", "Log Analytics", "Application Insights", "Activity Log"
- Task involves monitoring configuration, alert setup, log queries, metric retrieval
- Keywords: monitor, metric, alert, log analytics, application insights, diagnostic setting, activity log, action group, alert rule
- Resource health checks, performance monitoring, diagnostic configuration

### SHOULD NOT Use When
- Billing only → delegate to: `azure-cost-ops`
- RBAC/IAM only → delegate to: `azure-rbac-ops`
- Resource creation (compute/storage) → delegate to: specific service skill
- Network configuration → delegate to: `azure-network-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.target_resource_id}}` | User input | Resource being monitored; ask once |
| `{{user.action_group_name}}` | User input | Action group name for alerts |
| `{{user.alert_rule_name}}` | User input | Alert rule name |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Monitor Components

### 1. Metrics
Azure Metrics provide numerical data about resource performance.

#### Retrieve Metrics — Azure CLI (Primary)
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

#### Retrieve Metrics — Azure SDK (Fallback)
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.monitor import MonitorManagementClient
import os

credential = DefaultAzureCredential()
client = MonitorManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

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

### 2. Alerts (Alert Rules + Action Groups)

#### Create Action Group — Azure CLI
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

#### Create Metric Alert Rule — Azure CLI
```bash
# Create metric alert rule
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

#### Create Log Alert Rule — Azure CLI
```bash
# Create scheduled query rule (log alert)
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

### 3. Log Analytics

#### Query Logs — Azure CLI
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

#### Query Logs — Azure SDK
```python
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient
import os

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

### 4. Diagnostic Settings

#### Enable Diagnostic Settings — Azure CLI
```bash
# Create diagnostic setting to send logs to Log Analytics
az monitor diagnostic-settings create \
  --name "{{user.diagnostic_setting_name}}" \
  --resource "{{user.target_resource_id}}" \
  --workspace "{{user.workspace_id}}" \
  --logs "[{category:'Administrative',enabled:true},{category:'Security',enabled:true}]" \
  --metrics "[{category:'AllMetrics',enabled:true,timegrain:'PT1M'}]" \
  --output json
```

### 5. Activity Log (Audit Trail)

#### Query Activity Log — Azure CLI
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

### Operation: Delete Alert Rule

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

```bash
# Show alert rule before deletion
az monitor metrics alert show --name "{{user.alert_rule_name}}" --resource-group "{{user.resource_group}}" --output json

# Request confirmation - user must type exact alert rule name
# Then proceed with deletion:
az monitor metrics alert delete --name "{{user.alert_rule_name}}" --resource-group "{{user.resource_group}}" --output json
```

## Common Metric Namespaces

| Namespace | Metrics |
|-----------|---------|
| `Microsoft.Compute/virtualMachines` | Percentage CPU, Network In/Out, Disk Read/Write |
| `Microsoft.Storage/storageAccounts` | BlobCapacity, BlobCount, Transactions, Ingress/Egress |
| `Microsoft.Sql/servers` | CPU_percent, Storage_used, Active_connections |
| `Microsoft.Web/sites` | CPU Time, Requests, Response Time, Memory Working Set |
| `Microsoft.Network/loadBalancers` | VipAvailability, DipAvailability, ByteCount |
| `Microsoft.Insights/components` | Requests, Exceptions, Availability, Dependencies |

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate.
See `AGENTS.md §3–§8` for the spec.

| Parameter | Value |
|-----------|-------|
| GCL | **recommended** |
| max_iterations | 3 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE alert rule (`az monitor metrics alert delete`) → **required**; monitoring gap warning + Safety=0 → ABORT
- DELETE action group (`az monitor action-group delete`) → **required**; check rule references + affected rules listed
- DELETE diagnostic setting → **required**; data flow gap communicated
- CREATE alert rule / action group / diagnostic setting → recommended
- QUERY metrics / logs / activity log (read-only) → optional (GCL may be skipped)

### Read-Only vs Write

Most Monitor operations are read-only (query, list, show). GCL is encouraged but not required
for read-only operations. All **delete** operations are required to go through GCL.

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Monitor Docs](https://docs.microsoft.com/azure/azure-monitor/)
- [Azure CLI Monitor Reference](https://docs.microsoft.com/cli/azure/monitor)
- [KQL Query Reference](https://docs.microsoft.com/azure/data-explorer/kusto/query/)
