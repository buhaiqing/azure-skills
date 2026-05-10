# Azure Monitor Troubleshooting

## Common API Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| InvalidParameter | 400 | Request validation failed | Fix args per Azure API docs |
| ResourceNotFound | 404 | Resource does not exist | Verify resource ID |
| AccessDenied | 403 | RBAC permission insufficient | HALT; add Monitoring Reader/Contributor role |
| QuotaExceeded | 400 | Alert/action group limit reached | HALT; request quota increase |
| ThrottlingException | 429 | Rate limit exceeded | Backoff; retry 3x |
| InternalError | 500 | Azure service error | Retry 3x; HALT |

## Diagnostic Order

1. **Verify credentials**: `az account show`
2. **Verify subscription**: Check `AZURE_SUBSCRIPTION_ID`
3. **Check resource ID format**: Verify full resource path
4. **Verify permissions**: User needs Monitoring Reader/Contributor
5. **Check metric namespace**: Verify namespace matches resource type
6. **Test KQL query**: Run query in Log Analytics portal
7. **Check diagnostic settings**: Verify logs flowing to workspace
8. **Review Activity Log**: Check recent operations

## Metrics Issues

### Issue: Metric not available for resource

**Symptoms**:
- Metric query returns empty results
- Metric definition list shows no metrics

**Diagnosis Steps**:
1. Check metric namespace matches resource type: `az monitor metrics list --resource {{resource_id}}`
2. Verify resource is in running state
3. Check if metric requires diagnostic settings enabled
4. Verify metric name is correct

**Resolution Options**:
- Option A: Enable diagnostic settings for the resource
- Option B: Use correct namespace for resource type
- Option C: Wait for metric data collection (some metrics need time)

### Issue: Metric alert not firing

**Symptoms**:
- Metric exceeds threshold but no alert
- Alert rule shows but never fires

**Diagnosis Steps**:
1. Check alert rule scope matches resource
2. Verify condition and threshold
3. Check action group is configured
4. Verify evaluation frequency and window size
5. Check metric data is flowing

**Resolution Options**:
- Option A: Adjust threshold or window size
- Option B: Verify action group notifications work
- Option C: Check metric aggregation type matches condition

## Alerts Issues

### Issue: Action group notifications not received

**Symptoms**:
- Alert fires but no email/webhook notification
- Notifications delayed or missing

**Diagnosis Steps**:
1. Check action group configuration: `az monitor action-group show`
2. Verify email addresses are correct
3. Test webhook endpoint accessibility
4. Check notification rate limits (email: max 100/hour)
5. Review alert history for fired alerts

**Resolution Options**:
- Option A: Fix email/webhook configuration
- Option B: Check notification throttling
- Option C: Verify webhook endpoint responds correctly

### Issue: Alert rule creation fails

**Symptoms**:
- Alert rule creation returns error
- "Invalid scope" or "Resource not found"

**Diagnosis Steps**:
1. Verify resource ID format is correct
2. Check resource exists in specified resource group
3. Verify metric/log supports alert type
4. Check subscription quota limits
5. Verify user has Monitoring Contributor role

**Resolution Options**:
- Option A: Fix resource ID format
- Option B: Create missing resource first
- Option C: Request quota increase

## Log Analytics Issues

### Issue: KQL query returns no results

**Symptoms**:
- Query executes but returns empty
- Expected data not showing

**Diagnosis Steps**:
1. Check time range in query (ago(1d) vs ago(1h))
2. Verify table exists in workspace
3. Check diagnostic settings are enabled for source resource
4. Verify workspace contains data for the resource
5. Test simpler query first (| take 10)

**Resolution Options**:
- Option A: Adjust time filter
- Option B: Enable diagnostic settings on source resource
- Option C: Verify correct table name

### Issue: Diagnostic settings not sending logs

**Symptoms**:
- Diagnostic settings configured but no logs in workspace
- Tables remain empty

**Diagnosis Steps**:
1. Check diagnostic setting: `az monitor diagnostic-settings show`
2. Verify workspace ID is correct
3. Check enabled log categories
4. Verify resource generates the log type
5. Wait for log ingestion delay (5-15 minutes)

**Resolution Options**:
- Option A: Fix workspace ID in diagnostic setting
- Option B: Enable correct log categories
- Option C: Wait for data to flow (delay possible)

### Issue: Query timeout

**Symptoms**:
- KQL query takes too long
- "Query timeout" error

**Diagnosis Steps**:
1. Simplify query (reduce joins, filters)
2. Check query complexity
3. Reduce time range
4. Check workspace size (large workspaces slower)

**Resolution Options**:
- Option A: Simplify query, reduce time range
- Option B: Use query best practices (filter early)
- Option C: Split query into smaller queries

## Activity Log Issues

### Issue: Activity log missing events

**Symptoms**:
- Expected operations not in activity log
- Log gaps for certain resources

**Diagnosis Steps**:
1. Check activity log retention (90 days default)
2. Verify query time range
3. Check caller filter (wrong caller filter)
4. Verify resource filter matches

**Resolution Options**:
- Option A: Adjust time range
- Option B: Remove caller filter or use correct caller
- Option C: Check event category filter

## Application Insights Issues

### Issue: No data in Application Insights

**Symptoms**:
- Application Insights shows no telemetry
- Empty requests, exceptions tables

**Diagnosis Steps**:
1. Check application instrumentation key
2. Verify SDK is initialized in application
3. Check network connectivity to Azure
4. Verify application is running and generating traffic

**Resolution Options**:
- Option A: Configure instrumentation key correctly
- Option B: Install/configure Application Insights SDK
- Option C: Check application network access

## Permission Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| "AccessDenied" | Missing Monitoring role | Add Monitoring Contributor role |
| "Cannot query workspace" | No workspace access | Add Log Analytics Reader role |
| "Cannot create alert" | No write permission | Add Monitoring Contributor role |

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Monitoring outage affecting production | Critical | Immediate Azure support ticket |
| Critical alerts not firing | High | Check config, then support |
| Log data loss | High | Support ticket |
| Query performance issues | Medium | Optimize query, then support if needed |
| Metric gaps | Medium | Check diagnostic settings |