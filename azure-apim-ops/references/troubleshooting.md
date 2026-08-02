# Azure API Management Troubleshooting

## Common API Error Codes

| Code (HTTP) | Meaning -> Action |
|-------------|-------------------|
| `InvalidParameter` (400) | Request validation failed -> Fix args per Azure API docs |
| `InvalidPublisherEmail` (400) | Publisher email malformed -> HALT; ask user for valid email |
| `ResourceNameInvalid` (400) | APIM name has invalid characters -> HALT; names must be 1-50 alphanum + hyphens |
| `CheckNameNotAvailable` (400) | Name conflict (globally unique) -> HALT; ask user for different name |
| `MismatchedResourceId` (400) | URL resource ID mismatch -> Verify RG and resource name |
| `AccessDenied` (403) | RBAC insufficient -> HALT; document required RBAC role |
| `ResourceNotFound` (404) | Service / API / Product does not exist -> Verify resource ID |
| `QuotaExceeded` (400/402) | Service limit reached -> HALT; user requests quota increase via Azure support |
| `ThrottlingException` (429) | Rate limit exceeded -> Backoff; retry 3x with exponential backoff |
| `InternalError` (500) | Azure service error -> Retry 3x; HALT |
| `ServiceUnavailable` (503) | APIM control plane down -> Retry 3x; HALT |
| `VNetInvalidSubnet` (400) | Subnet ID invalid or already used -> HALT; check subnet ID |
| `CertificateInvalid` (400) | Custom hostname SSL cert invalid -> HALT; re-upload valid cert |

## Diagnostic Order

1. **Verify credentials**: `az account show`
2. **Verify subscription**: `echo $AZURE_SUBSCRIPTION_ID`
3. **Verify resource group**: `az group show --name {{user.resource_group}}`
4. **Check APIM state**: `az apim show --name {{user.apim_name}} --resource-group {{user.resource_group}} --output json`
5. **Check provisioning state**: `properties.provisioningState` → `Succeeded`
6. **Check gateway URL**: `properties.gatewayUrl` → `https://{{user.apim_name}}.azure-api.net`
7. **Check developer portal**: `properties.developerPortalUrl` → `https://{{user.apim_name}}.developer.azure-api.net`
8. **Check policy**: `client.policy.get(...)` (SDK) — no CLI equivalent
9. **Check Activity Log**: `az monitor activity-log list --resource-id {{output.apim_id}}`
10. **Check Metrics**: `az monitor metrics list --resource {{output.apim_id}} --metric "Requests"`

## APIM Instance Issues

### Issue: APIM stuck in `Activating` / `Updating`

**Symptoms**: provisioningState != Succeeded after > 45 minutes.

**Diagnosis**:
1. `az apim show -n {{user.apim_name}} -g {{user.resource_group}} --output json` → check `provisioningState`
2. `az monitor activity-log list --resource-id {{output.apim_id}}` → look for failed operations
3. Check region capacity / planned maintenance (Azure status page)

**Resolution**:
- Option A: Wait — some SKU changes take 30-45 min
- Option B: `az apim delete -n {{user.apim_name}} -g {{user.resource_group}} --yes` then re-create (soft-delete recoverable for 48h)
- Option C: Open Azure support ticket

### Issue: `CheckNameNotAvailable`

**Symptoms**: `az apim create` returns `CheckNameNotAvailable`.

**Diagnosis**: APIM names are globally unique. Run `az apim check-name -n <candidate>` to verify availability.

**Resolution**:
- Option A: Append random suffix (e.g., `myapim7x9k`)
- Option B: Use different domain/brand name

### Issue: QuotaExceeded on create

**Symptoms**: `az apim create` fails with quota error.

**Diagnosis**: `az apim list --output json` → count existing instances; check region quotas.

**Resolution**: HALT — user must file Azure support request to raise quota.

## API / Product Issues

### Issue: 404 "Resource not found" on backend

**Symptoms**: APIM returns 404 for valid API path.

**Diagnosis**:
1. Verify API is associated with a Product: `client.product_api.list_by_product(...)` (SDK)
2. Verify subscription has access: `client.subscription.get(...)` (SDK)
3. Check `subscriptionRequired` on API — if true, missing key returns 404

**Resolution**:
- Add API to product via `az apim product api add -g {{user.resource_group}} -n {{user.apim_name}} --product-id {{user.product_id}} --api-id {{user.api_id}}`
- Pass subscription key: `-H "Ocp-Apim-Subscription-Key: {{output.primary_key}}"`

### Issue: 401 / 403 on backend

**Symptoms**: Backend rejects APIM-proxied request.

**Diagnosis**:
1. Check backend URL is correct: `properties.serviceUrl` on API
2. Check backend auth requirements (Function App function key, AAD, etc.)
3. Check policy for `<authentication-*>` blocks

**Resolution**:
- For Function App: use managed identity instead of function key in policy
- For AAD: add `<authentication-managed-identity resource="..."/>` in backend section

## Subscription Issues

### Issue: Primary key lost

**Symptoms**: Developer lost subscription primary key.

**Diagnosis**: Keys are write-only after creation. Cannot `get` primary key directly — must regenerate.

**Resolution**:
```python
client.subscription.regenerate_primary_key(
    resource_group_name='{{user.resource_group}}',
    service_name='{{user.apim_name}}',
    sid='{{user.subscription_id}}')
```
> WARNING: Regeneration invalidates all clients using the current key. Coordinate rollout.

### Issue: Subscription expired / disabled

**Symptoms**: API calls return 403 with subscription state mismatch.

**Diagnosis**: `client.subscription.get(...)` → check `properties.state`:
- `active` — OK
- `submitted` — awaiting approval (if product requires approval)
- `rejected` / `cancelled` / `expired` — denied

**Resolution**: Re-create subscription or update state via SDK `subscription.update(state='active')`.

## Policy Issues

### Issue: Policy XML invalid

**Symptoms**: `Error in element 'X' on line N, column M: ...`.

**Diagnosis**:
1. Validate XML well-formedness
2. Check element names against [APIM policy reference](https://learn.microsoft.com/azure/api-management/api-management-policies)
3. Check scope — `policyId="policy"` for global, `policyId="Operation/proxy"` per-operation

**Resolution**: Fix XML, re-apply via `client.api_policy.create_or_update(...)` (SDK).

### Issue: Policy change not taking effect

**Symptoms**: New policy not reflected in gateway behavior.

**Diagnosis**:
1. Confirm `create_or_update` returned 200/201
2. Wait 30-60s — policy changes propagate
3. Force gateway reload: `client.api_management_service.begin_update(...)` with `disable_gateway=true` then `false`

**Resolution**: Re-apply policy with correct scope; if persists, open APIM service restart via portal.

## VNet / Network Issues

### Issue: APIM in VNet mode unreachable

**Symptoms**: `https://{apim}.azure-api.net` times out from internet.

**Diagnosis**:
1. Confirm SKU: only Premium / Isolated supports VNet
2. Confirm NSG on subnet allows inbound 443 from internet (for External mode)
3. Confirm subnet has `Microsoft.ApiManagement/service` delegation

**Resolution**: For External mode — verify NSG rules; for Internal mode — use private endpoint or jumpbox.

## Performance Issues

### Issue: High latency

**Diagnosis**:
1. Check backend latency: Application Insights end-to-end transaction
2. Check APIM gateway latency: `az monitor metrics list --metric Duration`
3. Check cache hit rate: Application Insights custom metric or `<cache-lookup>` in policy

**Resolution**:
- Add `<cache-lookup>` policy for cacheable GETs
- Move to Premium SKU + multi-region
- Reduce backend latency (origin optimization)

### Issue: 429 Too Many Requests

**Symptoms**: Client receives 429.

**Diagnosis**: APIM throttle or backend throttle.
1. APIM: `<rate-limit>` policy too tight
2. Backend: backend unable to handle load

**Resolution**:
- Loosen `<rate-limit calls="..." renewal-period="...">` policy
- Increase backend scale
- Use `<retry>` policy client-side

## Activity Log Queries

```bash
# List all failed operations on APIM in last 24h
az monitor activity-log list \
  --resource-id "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.ApiManagement/service/{{user.apim_name}}" \
  --start-time "$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --status Failed \
  --output json

# List all delete operations on APIM
az monitor activity-log list \
  --resource-id "{{output.apim_id}}" \
  --operation "Microsoft.ApiManagement/service/delete" \
  --output json
```

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| APIM stuck in `Activating` > 1 hour | Critical | Open Azure support with activity log |
| Soft-delete expired, customer lost service | Critical | Azure support recovery (rare) |
| Gateway returning 5xx for all requests | High | Check backend health, APIM metrics |
| Policy change broke production traffic | High | Revert via SDK `api_policy.create_or_update` with previous XML |
| Subscription keys leaked in trace | Critical | Rotate immediately: `regenerate_primary_key` + `regenerate_secondary_key` |