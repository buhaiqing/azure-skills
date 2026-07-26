# AIOps — App Service RCA Rules

> AIOps-driven root cause analysis for Azure App Service anomalies.

## Detection Signals

| Signal | Source | Description |
|--------|--------|-------------|
| app_restart | `az monitor activity-log list` --resource-id <id> | App Service restart event |
| high_cpu | `az monitor metrics list` --metric "CpuPercentage" | CPU > 90% for > 5min |
| memory_pressure | `az monitor metrics list` --metric "MemoryPercentage" | Memory > 85% |
| cold_start_latency | `az monitor metrics list` --metric "ResponseTime" | Response time spike after idle period |
| app_crashed | `az webapp log tail` | Application crash in logs |

## RCA Rules

### Rule: App Restart Investigation
```
trigger: app_restart
flow:
  1. Check restart source: az monitor activity-log list --resource-id <id>
  2. If Azure-initiated: check platform health status
  3. If auto-heal triggered: check auto-heal rules in webapp config
  4. If manual restart: check who triggered it (caller info in Activity Log)
  5. Check app logs for crash information before restart
```

### Rule: CPU/Memory Pressure Resolution
```
trigger: high_cpu or memory_pressure
flow:
  1. Check App Service Plan pricing tier: az webapp show --name <app> --resource-group <rg> --query sku
  2. Check instance count: az webapp show --name <app> --resource-group <rg> --query siteConfig.numberOfWorkers
  3. Check app logs for long-running requests
  4. If consistently high:
     - Recommend scale up (higher tier) or scale out (more instances)
     - Check if auto-scale rules configured
     - If Linux: check if using dedicated vs shared tier
```

### Rule: Cold Start Optimization
```
trigger: cold_start_latency
flow:
  1. Check app is on Consumption/Elastic Premium plan (serverless)
  2. If cold start is frequent:
     - Recommend Premium V2/V3 plan for "always on"
     - If Functions: check for durable functions pattern
     - Consider: warm-up triggers, pre-warmed instances
```

### Rule: Application Crash Diagnosis
```
trigger: app_crashed
flow:
  1. Check app logs: az webapp log tail --name <app> --resource-group <rg>
  2. Check deployment history: az webapp deployment list --name <app> --resource-group <rg>
  3. If crash correlates with recent deployment:
     - Recommend rolling back: az webapp deployment source config-zip
  4. Check application settings: az webapp config show --name <app> --resource-group <rg>
     - Verify connection strings, API keys are valid

## Cross-Skill Integration

See `docs/cross-skill-rca-schema.md` for standard diagnostic paths and cross-service root cause analysis chains.

When this skill detects an anomaly that may involve other services:
- Delegate to `azure-monitor-ops` for metric correlation and Activity Log investigation
- Follow the standard diagnostic path defined in `docs/cross-skill-rca-schema.md`
```