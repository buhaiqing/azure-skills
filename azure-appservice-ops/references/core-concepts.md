# Core Concepts — Azure App Service

## Purpose

Azure App Service hosts managed web applications, REST APIs, and background web workloads without direct VM management. A Web App runs on an App Service Plan, which defines compute SKU, Location, worker count, and OS family.

## Resource Hierarchy

| Resource | Azure provider type | Notes |
|----------|---------------------|-------|
| App Service Plan | `Microsoft.Web/serverfarms` | Defines compute, SKU, OS, scaling boundary |
| Web App | `Microsoft.Web/sites` | Application resource; globally unique name |
| Deployment Slot | `Microsoft.Web/sites/slots` | Staging/production traffic swap boundary |
| App Settings | Site configuration | Treat secret-like values as sensitive |

Full Web App resource ID format:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Web/sites/{{user.webapp_name}}
```

Full App Service Plan resource ID format:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Web/serverfarms/{{user.plan_name}}
```

## App Service Plan Concepts

| Concept | Guidance |
|---------|----------|
| SKU | Free/Shared/Basic/Standard/Premium/Isolated families have different features |
| OS | Linux plans use `reserved=true`; Windows plans do not |
| Scale out | Worker count increases capacity within the plan |
| Scale up | SKU change can enable/disable slots, VNet integration, custom domains, autoscale |
| Plan sharing | Multiple apps can share one plan and compete for resources |

## Web App Concepts

| Feature | Notes |
|---------|-------|
| Runtime stack | `--runtime` or `linux_fx_version`, e.g., `PYTHON:3.11`, `NODE:20-lts` |
| App settings | Environment variables; mask values for keys containing password, secret, token, key, connection |
| Deployment slots | Reduce deployment risk; slot swap affects production routing |
| Logs | App logs, HTTP logs, deployment logs, and metrics help RCA |
| VNet integration | Outbound private access; does not make the app private by itself |
| Private endpoint | Inbound private access; coordinate with networking/DNS skills |

## Operation Boundaries

This skill owns Web App, App Service Plan, slots, runtime settings, lifecycle, logs, basic scale, app settings, and App Service diagnostics.

Delegate adjacent concerns:
- Container image registry and pull failures → `azure-acr-ops`
- Key Vault secret lifecycle → `azure-keyvault-ops`
- Front Door/custom edge routing → `azure-frontdoor-ops`
- Application Gateway/WAF ingress → `azure-appgateway-ops`
- VNet/subnet creation → `azure-vnet-ops`
- Database provisioning → database-specific skill

## Safety Rules

- Deleting a Web App removes hosted app configuration and stops traffic.
- Deleting an App Service Plan can affect every app attached to that plan.
- Stopping a production Web App causes downtime.
- Slot swap changes production traffic target.
- SKU downgrade can remove features or reduce capacity.
- App settings can contain secrets; never print unmasked sensitive values.

## Validation Commands

```bash
az appservice plan show --name "{{user.plan_name}}" --resource-group "{{user.resource_group}}" --output json
az webapp show --name "{{user.webapp_name}}" --resource-group "{{user.resource_group}}" --output json
az webapp deployment slot list --name "{{user.webapp_name}}" --resource-group "{{user.resource_group}}" --output json
az webapp log tail --name "{{user.webapp_name}}" --resource-group "{{user.resource_group}}"
```
