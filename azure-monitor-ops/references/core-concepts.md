# Azure Monitor Core Concepts

## What is Azure Monitor

- **Purpose**: Comprehensive monitoring, diagnostics, and alerting for Azure resources and applications
- **Category**: Monitoring / Observability
- **Portal**: https://portal.azure.com/#blade/Microsoft_Azure_Monitoring/AzureMonitoringBrowseBlade
- **Docs**: https://docs.microsoft.com/azure/azure-monitor/
- **Pricing**: https://azure.microsoft.com/pricing/details/monitor/

## Primary Components

| Component | Description | Portal Path |
|-----------|-------------|-------------|
| **Metrics** | Numerical performance data | Metrics blade per resource |
| **Alerts** | Alert rules + Action groups | Alerts blade |
| **Log Analytics** | Log aggregation and KQL queries | Log Analytics workspaces |
| **Application Insights** | Application performance monitoring | Application Insights resources |
| **Activity Log** | Audit trail of Azure operations | Activity Log blade |
| **Diagnostic Settings** | Log/metric export configuration | Diagnostic settings per resource |
| **Workbooks** | Interactive monitoring dashboards | Workbooks blade |
| **Dashboards** | Custom monitoring dashboards | Azure Dashboards |

## Architecture & Limits

### Data Flow

```
Azure Resources → Metrics → Azure Monitor → Alerts → Action Groups → Notifications
                 ↓
Azure Resources → Logs → Log Analytics → KQL Queries → Workbooks/Dashboards
                 ↓
Applications → Application Insights → Metrics/Logs → Analysis
```

### Quotas

| Quota | Limit | Adjustable |
|-------|-------|------------|
| Metric alerts per subscription | 1000 | Yes (support ticket) |
| Action groups per subscription | 1000 | Yes |
| Log Analytics workspace retention | 30-730 days | Configurable |
| Log queries per minute | 200 | No |
| Metrics retention | 90 days | No (standard) |

### Log Analytics Workspace SKU

| SKU | Use Case |
|-----|----------|
| **PerGB2018** | General purpose, pay per GB |
| **CapacityReservation** | High volume, reserved capacity |
| **Free** | Dev/test, limited 500MB/day |
| **PerNode** | Legacy, pay per node |

## Metrics Overview

### Metric Structure

```
Namespace: Microsoft.Compute/virtualMachines
Metric: Percentage CPU
Dimensions: Optional (e.g., VM name)
Aggregation: Average, Minimum, Maximum, Count, Total
Interval: PT1M, PT5M, PT1H
```

### Metric Aggregations

| Aggregation | Description |
|-------------|-------------|
| **Average** | Average value over time window |
| **Minimum** | Minimum value |
| **Maximum** | Maximum value |
| **Count** | Number of samples |
| **Total** | Sum of all values |

### Metric Retention
- **Standard metrics**: 90 days
- **Custom metrics**: 90 days
- **Extended retention**: Available via diagnostic settings to storage

## Alerts Overview

### Alert Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Metric Alerts** | Based on metric values | CPU > 80%, latency > 500ms |
| **Log Alerts** | Based on KQL query results | Error count > threshold |
| **Activity Log Alerts** | Based on Azure operations | VM restart, resource deletion |
| **Smart Alerts** | ML-based anomaly detection | Application Insights smart detection |

### Alert Components

1. **Scope**: Target resource(s) to monitor
2. **Condition**: Criteria for firing alert
3. **Action Group**: Notification/automation actions
4. **Severity**: 0-4 (Critical to Verbose)

### Alert Severity Levels

| Severity | Description |
|----------|-------------|
| **Sev0** | Critical - Immediate attention |
| **Sev1** | Error - Urgent attention |
| **Sev2** | Warning - Prompt attention |
| **Sev3** | Informational - Awareness |
| **Sev4** | Verbose - Informational |

### Action Group Actions

| Action Type | Description |
|-------------|-------------|
| **Email/SMS** | Email and SMS notifications |
| **Webhook** | HTTP POST to endpoint |
| **Azure Function** | Trigger Azure Function |
| **Logic App** | Trigger Logic App workflow |
| **Event Hub** | Send to Event Hub |
| **ITSM** | Connect to ITSM system |
| **Secure Webhook** | Authenticated webhook |

## Log Analytics Overview

### Workspace Structure

| Element | Description |
|---------|-------------|
| **Workspace** | Container for logs |
| **Tables** | Log data organized by type |
| **Solutions** | Pre-built monitoring packs |
| **Saved Queries** | Reusable KQL queries |

### Common Tables

| Table | Description |
|-------|-------------|
| `AzureActivity` | Azure activity/audit log |
| `AzureMetrics` | Metrics exported to logs |
| `Syslog` | Linux system logs |
| `Event` | Windows event logs |
| `Heartbeat` | Agent health status |
| `Perf` | Performance counter data |
| `AppAvailabilityResults` | Application Insights availability |
| `AppRequests` | Application Insights requests |
| `AppExceptions` | Application Insights exceptions |

### KQL (Kusto Query Language) Basics

```kql
// Basic query
AzureActivity | take 10

// Time filter
AzureActivity | where TimeGenerated > ago(1h)

// Filter by field
AzureActivity | where OperationName == 'RestartVM'

// Aggregation
AzureActivity | count by OperationName

// Sorting
AzureActivity | top 10 by TimeGenerated desc

// Join tables
AzureActivity | join kind=inner (AzureMetrics) on ResourceId
```

## Application Insights Overview

### Features

| Feature | Description |
|---------|-------------|
| **Request Tracking** | HTTP request telemetry |
| **Exception Tracking** | Exception capture and analysis |
| **Dependency Tracking** | Database/API call monitoring |
| **Availability Tests** | URL ping/multi-step tests |
| **Performance Counters** | Server performance metrics |
| **Custom Events** | Application-specific telemetry |
| **Live Metrics Stream** | Real-time monitoring |

### Application Map
Visualizes application dependencies and call flow:
- Web app → Database
- Web app → External API
- Service A → Service B

## Activity Log Overview

### Event Categories

| Category | Description |
|----------|-------------|
| **Administrative** | Azure resource operations (create, update, delete) |
| **Security** | Security events (login, permission changes) |
| **ServiceHealth** | Azure service health events |
| **ResourceHealth** | Resource health status changes |
| **Alert** | Alert activation events |
| **Autoscale** | Autoscale operations |
| **Recommendation** | Azure Advisor recommendations |

### Common Operations to Monitor

- VM restart/delete
- Storage account creation/deletion
- Network configuration changes
- RBAC assignments
- Key Vault access
- Resource group deletion

## Diagnostic Settings Overview

### Export Destinations

| Destination | Description |
|-------------|-------------|
| **Log Analytics** | Real-time log/metric streaming |
| **Storage Account** | Archive logs for long-term retention |
| **Event Hub** | Stream to external systems |
| **Partner Solution** | Third-party monitoring |

### Data Types

| Data Type | Description |
|-----------|-------------|
| **Logs** | Activity log, resource logs |
| **Metrics** | Resource performance metrics |

## Best Practices

### Metrics
- Use appropriate aggregation for alert thresholds
- Set meaningful alert thresholds based on baseline
- Monitor critical metrics: CPU, Memory, Network, Disk

### Alerts
- Define clear severity levels
- Use action groups for consistent notifications
- Configure webhook for automation
- Set appropriate evaluation frequency

### Log Analytics
- Configure diagnostic settings for all critical resources
- Use retention policy based on compliance requirements
- Create saved queries for common investigations
- Use workbooks for dashboards

### Application Insights
- Instrument all critical applications
- Enable dependency tracking
- Set up availability tests for public endpoints
- Use smart detection for anomaly alerts

## Pricing Model

- **Metrics**: Free for standard metrics
- **Alerts**: Metric alerts per month, log alerts per query
- **Log Analytics**: Per GB ingested and retained
- **Application Insights**: Per GB ingested
- **Estimator**: https://azure.microsoft.com/pricing/calculator/