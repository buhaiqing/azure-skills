# Azure Functions Troubleshooting Guide

## Common API Error Codes

| Code (HTTP) | Meaning -> Action |
|-------------|-------------------|
| InvalidParameter (400) | Request validation failed -> Fix args per Azure REST API docs |
| NameUnavailable (400/409) | Function App name globally taken -> Suggest alternative unique name |
| StorageAccountNotFound (400) | Consumption plan storage missing -> HALT; provision via `azure-blobstorage-ops` |
| AccessDenied (403) | RBAC permission insufficient -> HALT; user updates RBAC role |
| AuthorizationFailed (403) | Operation not permitted -> HALT; check RBAC assignment |
| ResourceNotFound (404) | Function App not found -> Verify name and resource group |
| Conflict (409) | App already exists or state conflict -> Check current app state |
| QuotaExceeded (400/402) | Plan/instance quota reached -> HALT; request quota increase |
| ThrottlingException (429) | Rate limit exceeded -> Retry with exponential backoff |
| InternalError (500) | Azure service error -> Retry 3x; HALT with correlation ID |
| ServiceUnavailable (503) | Service temporarily down -> Retry 3x; HALT |

## Diagnostic Order

### Function App Not Running / Errors

1. **Verify credentials**: `az account show`
2. **Verify subscription**: `az account list`
3. **Verify app exists**: `az functionapp show --name {{user.function_app_name}} --resource-group {{user.resource_group}}`
4. **Check app settings**: `az functionapp config appsettings list`
5. **Check logs**: `az functionapp log tail --name {{user.function_app_name}} --resource-group {{user.resource_group}}`
6. **Check Activity Log**: `az monitor activity-log list`

### Cold Start (Consumption)

**Symptoms**:
- First invocation after idle takes seconds (up to ~10s for .NET/Java)
- Subsequent calls fast

**Diagnosis**:
```bash
az functionapp show --name {{user.function_app_name}} --resource-group {{user.resource_group}} --query "state"
az monitor metrics list \
  --resource "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Web/sites/{{user.function_app_name}}" \
  --metric "FunctionExecutionCount" --output json
```

**Resolution**:
- Accept cold start on Consumption, OR
- Migrate to **Premium** plan (pre-warmed instances) via `azure-appservice-ops`
- Reduce package size / use ReadyToRun for .NET

### Timeout (Function Execution)

**Symptoms**:
- HTTP 500 / 503 after fixed duration
- "Timeout value ... exceeded"

**Diagnosis**: Check `functionTimeout` in `host.json` and plan limits.
**Resolution**:
- Consumption default hard limit 5 min (max 10 min via config)
- Premium/Dedicated allow longer durations (up to 60 min with `functionTimeout: -1`)
- Split work or move to Durable Functions

### Deployment Failure (zip push)

**Symptoms**:
- Deploy returns non-zero; app not updated
- "No usable version identified"

**Diagnosis**:
```bash
az functionapp deployment list --name {{user.function_app_name}} --resource-group {{user.resource_group}} --output json
az functionapp log tail --name {{user.function_app_name}} --resource-group {{user.resource_group}}
```

**Resolution**:
- Verify `FUNCTIONS_WORKER_RUNTIME` matches deployed language
- Verify zip contains `host.json` + function folder with `function.json`
- For Python, ensure `requirements.txt` present for remote build

### Missing Dependencies (Runtime Error)

**Symptoms**: Module/package not found at runtime
**Resolution**:
- Python: include `requirements.txt`; let Azure remote-build
- .NET: publish as self-contained or rely on extension bundles
- Node: `package.json` with deps in zip root

### App Settings / Connection String Wrong

**Symptoms**: Function fails to bind to storage/queue/event hub
**Resolution**:
```bash
az functionapp config appsettings list --name {{user.function_app_name}} --resource-group {{user.resource_group}} --output json
# Verify AzureWebJobsStorage and trigger connection strings point to correct resource
```

## Activity Log for Debugging

```bash
az monitor activity-log list \
  --resource "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Web/sites/{{user.function_app_name}}" \
  --start-time "2026-07-11T00:00:00Z" --output json
```

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Production function app down affecting users | Critical | Immediate Azure support ticket |
| Data loss (delete without confirm) | Critical | Immediate support + backup review |
| Persistent provisioning failures | High | Support ticket with Activity Log |
| Quota/capacity issues | Medium | Quota increase request |
| Performance / cold start | Medium | Plan review |
