# Azure Traffic Manager Troubleshooting

## Common API Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| InvalidParameter | 400 | Request validation failed | Fix args per Azure API docs |
| NameNotAvailable | 400 | DNS name not unique | HALT; choose unique DNS name |
| InvalidRoutingMethod | 400 | Routing method incompatible | Fix routing method |
| AccessDenied | 403 | RBAC permission insufficient | HALT; user updates RBAC role |
| ResourceNotFound | 404 | Resource does not exist | Verify resource ID |
| QuotaExceeded | 400 | Service limit reached | HALT; user requests quota increase |
| ThrottlingException | 429 | Rate limit exceeded | Backoff; retry 3x |
| InternalError | 500 | Azure service error | Retry 3x; HALT |

## Diagnostic Order

1. **Verify credentials**: `az account show`
2. **Verify subscription**: Check `AZURE_SUBSCRIPTION_ID`
3. **Verify resource group**: `az group show --name {{rg}}`
4. **Check Traffic Manager profile**: `az network traffic-manager profile show`
5. **Check endpoint health**: `az network traffic-manager endpoint show`
6. **Verify DNS resolution**: `dig {{dns-name}}.trafficmanager.net`
7. **Check routing method**: Verify correct routing method
8. **Check Activity Log**: `az monitor activity-log list`

## Traffic Manager Issues

### Issue: Traffic routing to wrong endpoint

**Symptoms**:
- Users routed to unexpected endpoint
- Geographic routing not working correctly

**Diagnosis Steps**:
1. Check routing method: `az network traffic-manager profile show`
2. Verify endpoint priorities/weights/geo-mapping
3. Test DNS resolution from different locations
4. Check endpoint health status
5. Verify TTL settings

**Resolution Options**:
- Option A: Fix endpoint configuration (priority/weight)
- Option B: Update geographic mapping
- Option C: Change routing method

### Issue: Endpoint shows degraded status

**Symptoms**:
- Endpoint marked as degraded
- Not receiving traffic (for non-weighted routing)

**Diagnosis Steps**:
1. Check endpoint status: `az network traffic-manager endpoint show`
2. Verify target server is running
3. Check health probe configuration
4. Verify probe protocol/port/path
5. Check target server responds to probe

**Resolution Options**:
- Option A: Fix target server to respond on probe path
- Option B: Update health probe configuration
- Option C: Check firewall allows probe traffic

### Issue: DNS name not resolving

**Symptoms**:
- DNS queries fail
- trafficmanager.net name not found

**Diagnosis Steps**:
1. Check profile status: `az network traffic-manager profile show`
2. Verify profile is enabled
3. Check DNS configuration in profile
4. Verify endpoints exist
5. Test with dig/nslookup

**Resolution Options**:
- Option A: Enable profile
- Option B: Add endpoints to profile
- Option C: Verify DNS name is unique

### Issue: Failover not happening

**Symptoms**:
- Traffic not switching to backup endpoint
- Primary endpoint offline but still receiving traffic

**Diagnosis Steps**:
1. Check endpoint monitor status
2. Verify health probe is detecting failure
3. Check routing method is Priority
4. Verify backup endpoint exists and is enabled
5. Check TTL values (high TTL delays failover)

**Resolution Options**:
- Option A: Lower TTL for faster failover
- Option B: Verify health probe detects failure
- Option C: Check backup endpoint priority

## DNS Name Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| "NameNotAvailable" | DNS name already used | Choose unique name |
| DNS not resolving | Profile disabled | Enable profile |

## Endpoint Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| Endpoint degraded | Health probe failing | Fix target server/probe config |
| Endpoint inactive | Profile issues | Check profile status |
| Geographic routing wrong | Mapping incorrect | Update geo-mapping |

## Health Probe Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| False positive failures | Probe config wrong | Adjust probe settings |
| Slow detection | Probe interval too high | Lower probe interval |
| Port unreachable | Target firewall | Allow probe port |

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Global routing failure | Critical | Immediate Azure support ticket |
| Failover not working | High | Check probes, then support |
| Geographic routing incorrect | Medium | Verify mappings |
| DNS resolution issues | High | Check profile status |