# Azure Load Balancer Troubleshooting

## Common API Error Codes

| Code (HTTP) | Meaning -> Action |
|-------------|-------------------|
| InvalidParameter (400) | Request validation failed -> Fix args per Azure API docs |
| InvalidParameterValue (400) | Specific field invalid -> Check allowed values |
| MissingParameter (400) | Required field omitted -> Add missing parameter |
| AccessDenied (403) | RBAC permission insufficient -> HALT; user updates RBAC role |
| ResourceNotFound (404) | Resource does not exist -> Verify resource ID and resource group |
| Conflict (409) | Resource already exists or state conflict -> Check current state |
| QuotaExceeded (400) | Service limit reached -> HALT; user requests quota increase |
| ThrottlingException (429) | Rate limit exceeded -> Backoff; retry 3x |
| InternalError (500) | Azure service error -> Retry 3x; HALT with correlation ID |
| ServiceUnavailable (503) | Service temporarily down -> Retry 3x; HALT |

## Diagnostic Order

1. **Verify credentials**: `az account show`
2. **Verify subscription**: Check `AZURE_SUBSCRIPTION_ID`
3. **Verify resource group**: `az group show --name {{rg}}`
4. **Check Load Balancer state**: `az network lb show --name {{lb}} --resource-group {{rg}}`
5. **Check backend pool members**: `az network lb address-pool show`
6. **Check health probes**: `az network lb probe show`
7. **Check NSG rules**: `az network nsg show`
8. **Check Activity Log**: `az monitor activity-log list`

## Load Balancer Issues

### Issue: Backend VMs not receiving traffic

**Symptoms**:
- Traffic not reaching backend VMs
- Health probe shows healthy but no connections

**Diagnosis Steps**:
1. Check backend pool membership: `az network lb address-pool show`
2. Verify VM NIC is in backend pool
3. Check NSG rules on backend subnet allow traffic
4. Verify load balancing rule is configured
5. Check frontend IP configuration

**Resolution Options**:
- Option A: Add VM NIC to backend pool
- Option B: Update NSG rules to allow traffic
- Option C: Check load balancing rule frontend/backend ports

### Issue: Health probe shows degraded

**Symptoms**:
- Backend pool members marked as degraded
- Traffic not routed to backend

**Diagnosis Steps**:
1. Check health probe configuration: `az network lb probe show`
2. Verify backend VM is running
3. Check probe protocol matches application (HTTP vs TCP)
4. Verify probe port matches application port
5. Check NSG allows probe traffic

**Resolution Options**:
- Option A: Fix application to respond on probe port
- Option B: Update probe port/protocol configuration
- Option C: Update NSG rules for probe traffic

### Issue: Connection timeout from frontend

**Symptoms**:
- Clients cannot connect to Load Balancer frontend
- Connection timeouts

**Diagnosis Steps**:
1. Check frontend IP is accessible (ping for public IP)
2. Verify load balancing rule exists
3. Check frontend port matches expected port
4. Verify backend pool has healthy members
5. Check NSG on frontend (if applicable)

**Resolution Options**:
- Option A: Create or fix load balancing rule
- Option B: Ensure backend pool has healthy members
- Option C: Check public IP is created and assigned

## Credential Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| "Unable to authenticate" | No credentials | Run `az login` or configure env vars |
| "AuthorizationFailed" | Missing RBAC | Add Network Contributor role |
| "Subscription not found" | Wrong ID | Verify AZURE_SUBSCRIPTION_ID |

## NSG Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| Backend not receiving traffic | NSG blocking | Add rule to allow LB traffic |
| Health probe failing | NSG blocking probe port | Add rule for probe protocol/port |
| Inbound NAT failing | NSG blocking NAT port | Add rule for NAT frontend port |

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Production outage | Critical | Immediate Azure support ticket |
| Backend connectivity issues | High | Check NSG, then support if unresolved |
| Persistent provisioning failures | High | Support ticket with correlation IDs |
| Unexpected quota limits | Medium | Quota increase request |