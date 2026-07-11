# Azure Container Instances Troubleshooting

## API Error Codes (compact)

| Error | HTTP | Meaning | Agent Action |
|-------|------|---------|--------------|
| InvalidParameter | 400 | Bad arg (image/cpu/memory/port) | Fix per Azure REST docs; retry once |
| InvalidImage | 400 | Image not resolvable | Verify image name/registry; delegate `azure-acr-ops` for registry |
| AuthorizationFailed | 403 | RBAC/registry auth insufficient | HALT; check RBAC + registry creds (delegate `azure-acr-ops`) |
| ResourceNotFound | 404 | Group/container/RG missing | Verify names, subscription, RG |
| Conflict | 409 | Name collision / state conflict | Check current group state |
| QuotaExceeded | 400/402 | Regional CPU/memory/GPU quota hit | HALT; request quota increase |
| Throttling | 429 | Rate limited | Backoff; retry ≤3x |
| InternalError | 500 | Azure service error | Retry ≤3x; HALT with correlation ID |
| ServiceUnavailable | 503 | Transient outage | Retry ≤3x; HALT |

## Diagnostic Order

1. **Credentials**: `az account show`
2. **Group state**: `az container show --name {{cg}} --resource-group {{rg}} --output json`
3. **Events**: `az container show ... --query "containers[].instanceView.events"`
4. **Logs**: `az container logs --name {{cg}} --resource-group {{rg}} --container-name {{container}}`
5. **Activity Log**: `az monitor activity-log list --resource /subscriptions/{{sub}}/.../containerGroups/{{cg}}`
6. **Registry auth**: if `ImagePullBackOff`, delegate RCA to `azure-acr-ops`.

## Common Failures

### Image pull failure
- **Symptom**: group `Failed`, event `Failed to pull image`.
- **Causes**: wrong image tag, private registry without creds, ACR firewall/DNS, network rule set.
- **Action**: verify `--registry-*` creds; for ACR auth/network → `azure-acr-ops`. Public Docker Hub rate limits may also apply.

### OOM / crash loop
- **Symptom**: container restarts repeatedly; `OOMKilled` in events.
- **Action**: raise `--memory`; check app for leaks; set `restartPolicy: Never` to capture terminal logs.

### Container exits immediately (Succeeded/Failed)
- **Action**: `az container logs`; with `restartPolicy: Never` the container stays stopped so logs persist.

### Network / no public IP
- **Symptom**: `ipAddress` null or unreachable.
- **Action**: ensure `--ip-address public`; for private VNet injection verify subnet delegated to Microsoft.ContainerInstance → delegate `azure-vnet-ops` / `azure-privateendpoint-ops`.

### Quota exceeded
- **Action**: `az container list-usage --location {{location}}`; request increase or pick different region/SKU.

## Recovery Matrix (HALT vs Retry)

| Condition | Action |
|-----------|--------|
| QuotaExceeded / AuthorizationFailed | HALT |
| InvalidParameter (bad flag) | Fix arg; retry once |
| Throttling / 429 | Backoff; retry ≤3x |
| 5xx / network | Retry ≤3x; HALT with correlation ID |
| Destructive op without confirmation | HALT; require explicit confirm |

## Activity Log for Debugging

```bash
az monitor activity-log list \
  --resource "/subscriptions/{{sub}}/resourceGroups/{{rg}}/providers/Microsoft.ContainerInstance/containerGroups/{{cg}}" \
  --output json
```
