# Troubleshooting — azure-audit-ops

> Error codes and diagnostics for Azure audit operations.

## Error Recovery Table

| Error | Probable Cause | Action |
|-------|---------------|--------|
| AuthorizationFailed | Insufficient RBAC permissions (needs Reader or higher) | HALT; assign Reader role to Service Principal |
| InvalidTimeRange | Malformed time format in activity log query | Fix time format: `2026-01-01T00:00:00Z` |
| TooManyRequests (429) | API rate limit exceeded | Backoff 30s, retry with smaller scope |
| SubscriptionNotFound | Invalid subscription ID | HALT; verify subscription ID |
| ResourceNotFound | Resource ID or name is wrong | HALT; verify resource exists |
| 5xx Internal | Azure server error | Retry 3x with backoff, then HALT |
| ActivityLogsDisabled | Activity Log not enabled for subscription | HALT; check Microsoft.Insights provider registration |
| RoleAssignmentNotFound | No role assignments found for filter | Return empty result (not an error) |
| LockNotFound | No locks found for scope | Return empty result (not an error) |
| InvalidQueryFilter | Malformed filter expression | Fix filter syntax; retry once |
| GatewayTimeout (504) | Large query taking too long | Reduce time range or scope; retry |

## Common Issues

### Activity Log returns empty results
- **Check 1**: Time range is in the past 90 days (default retention)
- **Check 2**: User/SP has `Microsoft.Insights/eventtypes/values/read` permission
- **Check 3**: Filter syntax is correct (see `az monitor activity-log list --help`)

### RBAC query times out for large organizations
- **Solution**: Scope to resource group level instead of subscription
- **Solution**: Use `--include-inherited` carefully (adds processing time)

### NSG audit misses some rules
- **Caveat**: The `--query` filter only checks `securityRules` — it does NOT check `defaultSecurityRules` (default Azure rules: `AllowVnetInBound`, `DenyAllInbound`, etc.)
- **Fix**: Explicitly exclude default rules: `[?access=='Allow' && sourceAddressPrefix=='*' && !contains(name,'AllowVnet') && !contains(name,'DenyAll')]`

### Diagnostic Settings list shows incomplete results
- **Caveat**: `az monitor diagnostic-settings list` only shows settings for a **single resource**. You must iterate over all resources for a full scan.
- **Recommendation**: Use Azure SDK for Python for comprehensive sweeps.

### Policy compliance query returns old data
- **Caveat**: Policy compliance evaluation is not real-time. Use `az policy state trigger-scan` to force re-evaluation, but this may take minutes.

## Verification Commands

```bash
# Verify Activity Log is enabled
az provider show --namespace Microsoft.Insights --query "registrationState"

# Verify RBAC permissions
az role assignment list --assignee "{{principal_id}}" --query "[].roleDefinitionName"

# Verify resource exists
az resource show --ids "{{target_resource_id}}"

# Test Activity Log query (minimal)
az monitor activity-log list --max-events 1 --output json

# Test lock query
az lock list --output json --query "length(@)"
```

## Rate Limits

| API | Limit | Notes |
|-----|-------|-------|
| Activity Log (list) | 100 req/min per subscription | Backoff if throttled |
| Role Assignment (list) | 500 req/min per tenant | Scope down to RG |
| Policy State (list) | 100 req/min per subscription | Use filters |
| Resource (list) | 1000 req/min per subscription | Use --resource-type to narrow |