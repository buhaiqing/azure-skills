# Troubleshooting Template (Azure Services)

Use this template when creating `references/troubleshooting.md` for a new Azure service skill.

## Common Error Codes Template

```markdown
## Common API Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| InvalidParameter | 400 | Request validation failed | Fix args per Azure REST API docs |
| InvalidParameterValue | 400 | Specific field invalid | Check allowed values |
| MissingParameter | 400 | Required field omitted | Add missing parameter |
| AccessDenied | 403 | RBAC permission insufficient | HALT; user updates RBAC role |
| AuthorizationFailed | 403 | Operation not permitted | HALT; check RBAC assignment |
| ResourceNotFound | 404 | Resource does not exist | Verify resource ID and resource group |
| NotFound | 404 | Subscription/resource group not found | Verify subscription ID |
| Conflict | 409 | Resource already exists or state conflict | Check current state |
| QuotaExceeded | 400/402 | Service limit reached | HALT; user requests quota increase |
| ServiceQuotaExceededException | 400 | Service quota limit | HALT; request support ticket |
| ThrottlingException | 429 | Rate limit exceeded | Retry with exponential backoff |
| RequestLimitExceeded | 429 | Too many requests | Backoff; reduce request rate |
| InternalError | 500 | Azure service error | Retry 3x; HALT with correlation ID |
| ServiceUnavailable | 503 | Service temporarily down | Retry 3x; HALT |
| InsufficientCapacity | 500 | Azure capacity unavailable | Retry later or different location |
| ProvisioningFailed | N/A | Resource creation failed | Check error message; retry or HALT |
```

## Diagnostic Order Template

```markdown
## Diagnostic Order (General)

1. **Verify credentials**: `az account show`
2. **Verify subscription**: Check `AZURE_SUBSCRIPTION_ID`
3. **Verify resource group**: `az group show --name {{rg}}`
4. **Get resource by name**: `az [service] [resource] show --name {{name}} --resource-group {{rg}}`
5. **List related resources**: Check dependencies
6. **Check Activity Log**: `az monitor activity-log list`
7. **Check Azure Monitor metrics**: For performance issues
```

## Service-Specific Troubleshooting Sections

### Section 1: Credential Issues

```markdown
## Credential Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| "Unable to authenticate" | No credentials or expired | Run `az login` or configure env vars |
| "AuthorizationFailed" | Missing RBAC permission | Add required role to user/SP |
| "Subscription not found" | Wrong subscription ID | Verify AZURE_SUBSCRIPTION_ID |
| "Tenant not found" | Wrong tenant ID | Verify AZURE_TENANT_ID |
| "Invalid client secret" | Expired or wrong secret | Regenerate Service Principal secret |
```

### Section 2: Resource State Issues

```markdown
## Resource State Issues

| Provisioning State | Problem | Resolution |
|--------------------|---------|------------|
| stuck in "Creating" | Backend provisioning issue | Check Activity Log; contact Azure support |
| stuck in "Updating" | Operation timeout | Cancel and retry |
| "Failed" | Creation/update failed | Check error message in Activity Log |
| unexpected state transition | Configuration conflict | Review Activity Log; check dependencies |
```

### Section 3: Performance Issues

```markdown
## Performance Issues

| Symptom | Possible Cause | Resolution |
|---------|----------------|------------|
| Slow API response | Regional endpoint issue | Try different location |
| Timeout on large operations | Request size exceeds limit | Break into smaller batches |
| High latency | Network/routing issue | Check network connectivity, VNet |
| Provisioning takes too long | Backend capacity issue | Try different location |
```

### Section 4: Dependency Issues

```markdown
## Dependency Issues

| Error | Missing Dependency | Resolution |
|-------|-------------------|------------|
| "ResourceGroupNotFound" | RG ID invalid | Verify RG exists in subscription |
| "VirtualNetworkNotFound" | VNet not in RG | Verify VNet in same RG and location |
| "SubnetNotFound" | Subnet not in VNet | Check subnet in correct VNet |
| "StorageAccountNotFound" | SA not accessible | Verify SA exists and is accessible |
| "Invalid network interface" | NIC not found | Verify NIC in same RG |
```

## Example Troubleshooting Entry Format

```markdown
### Issue: VM fails to start

**Symptoms**:
- Azure VM stuck in "Creating" or "Starting" state
- Error message: "Provisioning failed"

**Diagnosis Steps**:
1. Check VM status: `az vm show --name {{vm}} --resource-group {{rg}} --output json`
2. Check Activity Log: `az monitor activity-log list --resource {{vm-resource-id}}`
3. Verify dependencies (VNet, NIC, Disk): `az vm list --resource-group {{rg}} --show-details`
4. Check capacity in location: `az vm list-skus --location {{location}} --output json`

**Resolution Options**:
- Option A: Use different VM size
- Option B: Try different location
- Option C: Check quota limits
- Option D: Cancel and retry: `az vm delete --name {{vm}} --resource-group {{rg}}`
```

## Activity Log Integration

```markdown
## Activity Log for Debugging

### Check recent operations
```bash
az monitor activity-log list \
  --caller "{{user-or-sp}}" \
  --start-time "2026-05-10T00:00:00Z" \
  --output json
```

### Check specific resource operations
```bash
az monitor activity-log list \
  --resource "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/{{provider}}/{{type}}/{{name}}" \
  --output json
```
```

## Support Escalation Criteria

```markdown
## When to Contact Azure Support

| Scenario | Severity | Action |
|----------|----------|--------|
| Production outage affecting users | Critical | Immediate support ticket |
| Data loss or corruption | Critical | Immediate support ticket |
| Security breach indicator | Critical | Immediate support + security review |
| Persistent 5xx errors after retries | High | Support ticket with correlation IDs |
| Unexpected quota limit behavior | Medium | Quota increase request via portal |
| Feature request or clarification | Low | Azure forums or documentation feedback |
```

## Azure-specific Troubleshooting Tools

```markdown
## Azure Diagnostic Tools

| Tool | Use Case | Command |
|------|----------|---------|
| Azure CLI | General diagnostics | `az [service] [resource] show` |
| Activity Log | Audit trail | `az monitor activity-log list` |
| Azure Monitor | Metrics | `az monitor metrics list` |
| Network Watcher | Connectivity | `az network watcher test-connectivity` |
| Resource Health | Service health | Portal: Resource Health blade |
| Azure Support | Escalation | Portal: Help + Support blade |
```