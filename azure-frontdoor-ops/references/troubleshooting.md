# Azure Front Door Troubleshooting

## Common API Error Codes

| Code (HTTP) | Meaning -> Action |
|-------------|-------------------|
| InvalidParameter (400) | Request validation failed -> Fix args per Azure API docs |
| NameNotAvailable (400) | Endpoint name not unique -> HALT; choose unique name |
| AccessDenied (403) | RBAC permission insufficient -> HALT; user updates RBAC role |
| ResourceNotFound (404) | Resource does not exist -> Verify resource ID |
| QuotaExceeded (400) | Service limit reached -> HALT; user requests quota increase |
| ThrottlingException (429) | Rate limit exceeded -> Backoff; retry 3x |
| InternalError (500) | Azure service error -> Retry 3x; HALT |

## Diagnostic Order

1. **Verify credentials**: `az account show`
2. **Verify subscription**: Check `AZURE_SUBSCRIPTION_ID`
3. **Verify resource group**: `az group show --name {{rg}}`
4. **Check Front Door profile**: `az afd profile show`
5. **Check endpoint status**: `az afd endpoint show`
6. **Check origin health**: `az afd origin show`
7. **Check origin group**: `az afd origin-group show`
8. **Check route configuration**: `az afd route show`
9. **Check WAF logs**: Azure Monitor logs

## Front Door Issues

### Issue: Origin health shows unhealthy

**Symptoms**:
- Origin marked as unhealthy
- Traffic not routing to origin

**Diagnosis Steps**:
1. Check origin status: `az afd origin show`
2. Verify origin server is running
3. Check health probe configuration: `az afd probe show`
4. Verify origin responds on probe path
5. Check origin certificate (HTTPS probe)
6. Verify network connectivity to origin

**Resolution Options**:
- Option A: Fix origin server to respond correctly
- Option B: Update health probe configuration
- Option C: Fix origin SSL certificate
- Option D: Check origin firewall rules

### Issue: Custom domain not working

**Symptoms**:
- Custom domain DNS resolves but fails
- SSL certificate errors

**Diagnosis Steps**:
1. Check custom domain: `az afd custom-domain show`
2. Verify DNS CNAME points to FD endpoint
3. Check SSL certificate status
4. Verify domain validation status

**Resolution Options**:
- Option A: Update DNS CNAME to correct endpoint
- Option B: Wait for SSL certificate provisioning
- Option C: Re-validate domain ownership

### Issue: WAF blocking legitimate requests

**Symptoms**:
- WAF blocks valid traffic
- 403 Forbidden responses

**Diagnosis Steps**:
1. Check security policy: `az afd security-policy show`
2. Review WAF logs in Azure Monitor
3. Identify rule causing block
4. Check request patterns

**Resolution Options**:
- Option A: Add WAF exclusion rule
- Option B: Change WAF mode to Detection
- Option C: Create custom allow rule

### Issue: Cache not working

**Symptoms**:
- No caching happening
- High origin load

**Diagnosis Steps**:
1. Check route cache settings: `az afd route show`
2. Verify cache is enabled
3. Check cache rules in rule set
4. Verify response headers allow caching
5. Check origin cache-control headers

**Resolution Options**:
- Option A: Enable caching on route
- Option B: Configure cache rules
- Option C: Fix origin cache-control headers

## Endpoint Name Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| "NameNotAvailable" | Name already used | Choose unique endpoint name |
| DNS not resolving | Wrong endpoint name | Verify endpoint hostname |

## Origin Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| Origin unreachable | Firewall/network | Check origin accessibility |
| SSL certificate error | Invalid certificate | Fix origin SSL |
| Health probe failing | Probe config wrong | Update probe settings |

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Global outage | Critical | Immediate Azure support ticket |
| WAF blocking all traffic | Critical | Disable WAF temporarily, then support |
| Origin connectivity issues | High | Check origin, then support |
| Custom domain SSL issues | Medium | Wait or re-validate domain |