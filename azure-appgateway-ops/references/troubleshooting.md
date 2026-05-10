# Azure Application Gateway Troubleshooting

## Common API Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| InvalidParameter | 400 | Request validation failed | Fix args per Azure API docs |
| InvalidSubnet | 400 | Subnet not dedicated for AGW | HALT; use dedicated subnet |
| SubnetInUse | 400 | Subnet already used | HALT; create new dedicated subnet |
| AccessDenied | 403 | RBAC permission insufficient | HALT; user updates RBAC role |
| ResourceNotFound | 404 | Resource does not exist | Verify resource ID |
| QuotaExceeded | 400 | Service limit reached | HALT; user requests quota increase |
| ThrottlingException | 429 | Rate limit exceeded | Backoff; retry 3x |
| InternalError | 500 | Azure service error | Retry 3x; HALT |

## Diagnostic Order

1. **Verify credentials**: `az account show`
2. **Verify subscription**: Check `AZURE_SUBSCRIPTION_ID`
3. **Verify resource group**: `az group show --name {{rg}}`
4. **Check Application Gateway state**: `az network application-gateway show`
5. **Check backend health**: `az network application-gateway show-backend-health`
6. **Check backend pool**: `az network application-gateway address-pool show`
7. **Check HTTP listener**: `az network application-gateway http-listener show`
8. **Check WAF logs**: Check Azure Monitor logs

## Application Gateway Issues

### Issue: Backend health shows unhealthy

**Symptoms**:
- Backend pool members marked unhealthy
- 502 Bad Gateway responses

**Diagnosis Steps**:
1. Check backend health: `az network application-gateway show-backend-health`
2. Verify backend servers are running
3. Check backend HTTP settings (port, protocol)
4. Verify backend servers respond on expected port
5. Check network connectivity (NSG, firewall)
6. Check probe path and protocol

**Resolution Options**:
- Option A: Fix backend application to respond correctly
- Option B: Update HTTP settings port/protocol
- Option C: Update probe configuration
- Option D: Check NSG rules for backend traffic

### Issue: SSL certificate error

**Symptoms**:
- SSL handshake failures
- Certificate not trusted

**Diagnosis Steps**:
1. Check SSL certificate: `az network application-gateway ssl-cert show`
2. Verify certificate is uploaded correctly
3. Check certificate expiration
4. Verify listener uses correct certificate
5. Check HTTPS listener configuration

**Resolution Options**:
- Option A: Re-upload valid certificate
- Option B: Update certificate password
- Option C: Create new HTTPS listener with correct cert

### Issue: 502 Bad Gateway

**Symptoms**:
- Clients receive 502 responses
- Backend connection failures

**Diagnosis Steps**:
1. Check backend health status
2. Verify backend pool has servers
3. Check backend HTTP settings
4. Verify backend servers are accessible
5. Check timeout settings

**Resolution Options**:
- Option A: Fix unhealthy backends
- Option B: Add backend servers to pool
- Option C: Adjust HTTP settings timeout

### Issue: WAF blocking legitimate requests

**Symptoms**:
- WAF blocks valid traffic
- False positives

**Diagnosis Steps**:
1. Check WAF policy: `az network application-gateway waf-policy show`
2. Review WAF logs for blocked requests
3. Identify rule causing block
4. Check OWASP CRS version

**Resolution Options**:
- Option A: Add exclusion rule for specific paths
- Option B: Change from Prevention to Detection mode
- Option C: Create custom allow rule

## Subnet Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| "SubnetInUse" | Subnet not dedicated | Create new subnet for AGW only |
| "InvalidSubnet" | Subnet too small | Subnet must have min 32 IPs |
| Subnet conflicts | Other resources in subnet | Move AGW to dedicated subnet |

## Capacity Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| Slow responses | Insufficient capacity | Increase instance count |
| Connection drops | Capacity limit | Enable autoscaling |
| High latency | Backend timeout | Adjust timeout settings |

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Production outage | Critical | Immediate Azure support ticket |
| WAF false positives blocking critical path | High | Review logs, adjust rules |
| Backend connectivity issues | High | Check NSG, then support |
| SSL certificate failures | Medium | Re-upload certificate |