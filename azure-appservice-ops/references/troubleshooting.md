# Troubleshooting — Azure App Service

## Error Decision Table

| Symptom / Error | Likely Cause | Action |
|-----------------|--------------|--------|
| `WebAppNameUnavailable` | Web App name is globally taken | HALT; ask for a unique name |
| `InvalidSku` | SKU unavailable in Location or unsupported feature | HALT; choose supported SKU |
| `QuotaExceeded` | Plan or worker quota reached | HALT; request quota increase or choose another Location/SKU |
| `AuthorizationFailed` | Missing Website Contributor/Contributor role | HALT; request RBAC fix |
| Runtime not accepted | Invalid runtime string for OS | HALT; list supported runtimes |
| Slot operation failed | SKU does not support slots or wrong slot names | HALT; verify SKU and slot list |
| VNet integration failed | Missing subnet delegation, unsupported SKU, or network mismatch | Delegate subnet checks to `azure-vnet-ops` |
| App returns 5xx | App runtime error, startup failure, dependency issue | Inspect logs, config, deployment status |
| `TooManyRequests` / 429 | Azure throttling | Backoff and retry up to 3 times |
| 5xx control-plane error | Azure transient issue | Retry up to 3 times, then HALT |

## Diagnostics Commands

```bash
az webapp show \
  --name "{{user.webapp_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,state:state,hostNames:hostNames,serverFarmId:serverFarmId,httpsOnly:httpsOnly}" \
  --output json

az webapp config show \
  --name "{{user.webapp_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

az webapp log config \
  --name "{{user.webapp_name}}" \
  --resource-group "{{user.resource_group}}" \
  --application-logging filesystem \
  --level information \
  --output json

az webapp log tail \
  --name "{{user.webapp_name}}" \
  --resource-group "{{user.resource_group}}"
```

## Deployment and Slot Checks

```bash
az webapp deployment list-publishing-profiles \
  --name "{{user.webapp_name}}" \
  --resource-group "{{user.resource_group}}" \
  --xml

az webapp deployment slot list \
  --name "{{user.webapp_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

Do not store publishing profile output in traces unless credentials are fully masked.

## App Settings Safety

Before logging app settings, mask values for keys matching case-insensitive patterns:

```text
password, pwd, secret, token, key, connection, connstr, credential, client_secret
```

Use key names and value presence only when auditing:

```bash
az webapp config appsettings list \
  --name "{{user.webapp_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "[].{name:name,slotSetting:slotSetting}" \
  --output json
```

## Polling Strategy

App Service create/update/delete operations can be long-running. Poll every 10 seconds for up to 15 minutes:

```bash
az webapp show \
  --name "{{user.webapp_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "state" \
  --output tsv
```

Expected state for running apps: `Running`. For delete verification, expected outcome is `ResourceNotFound`.

## Activity Log

```bash
az monitor activity-log list \
  --resource-group "{{user.resource_group}}" \
  --status Failed \
  --max-events 20 \
  --output json
```

Use Activity Log for RBAC, policy, quota, and control-plane failures.

## Safety Handling

- Never delete a plan before listing all apps attached to it.
- Never stop/restart production without warning about availability impact.
- Never swap slots without showing source and target.
- Never print publishing profiles, connection strings, or secret app setting values.
