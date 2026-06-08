# Azure Key Vault Troubleshooting and RCA

## Method: Evidence Before Conclusion

1. Confirm subscription, Resource Group, vault name, tenant, access model, network mode, purge protection, and target object metadata.
2. Build incident timeline: symptom start, deployments, identity changes, access-policy/RBAC changes, firewall/private endpoint changes, object version changes.
3. Identify whether failure is management plane or data plane.
4. Identify authorization model: RBAC or access policy.
5. Check identity, permissions, object state, and network path.
6. Correlate diagnostic logs, Activity Log, object metadata, and user-provided app errors.
7. Rank root-cause candidates by evidence and confidence.

## Symptom Index

| Symptom | First Evidence | Likely Area |
|---------|----------------|-------------|
| 403 Forbidden | access model, role/policy, identity object ID | RBAC/access policy |
| 401 Unauthorized | token/audience/tenant mismatch | identity/auth |
| Timeout / network unreachable | firewall, private endpoint, DNS | network |
| Secret not found | secret metadata, deleted state, version | name/version/deletion |
| Certificate near expiry | certificate attributes | lifecycle/renewal |
| Key operation denied | key permissions, disabled/expired key | crypto role/policy/key state |
| Purge blocked | purge protection/retention | safety control |
| App broke after secret rotation | secret version timeline + deploy | stale version/config |

## Triage Commands

```bash
az keyvault show \
  --name "{{user.vault_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,uri:properties.vaultUri,tenant:properties.tenantId,rbac:properties.enableRbacAuthorization,purgeProtection:properties.enablePurgeProtection,publicNetworkAccess:properties.publicNetworkAccess}" \
  --output json

az keyvault secret show \
  --vault-name "{{user.vault_name}}" \
  --name "{{user.secret_name}}" \
  --query "{id:id,attributes:attributes,tags:tags,contentType:contentType}" \
  --output json

az monitor activity-log list \
  --resource-group "{{user.resource_group}}" \
  --resource-id "{{output.vault_id}}" \
  --offset "{{user.analysis_window}}" \
  --output json
```

Do not query or print secret values during triage.

## Root Cause Rules

| Rule | Evidence Pattern | Confidence |
|------|------------------|------------|
| Wrong access model assumed | RBAC enabled but access policy checked, or inverse | High |
| Missing data-plane role | RBAC mode + principal lacks required Key Vault role | High |
| Missing access policy permission | access policy mode + principal lacks object permission | High |
| Wrong principal | app uses different managed identity/object ID than granted | High |
| Tenant mismatch | token tenant differs from vault tenant | High |
| Network deny | public access/firewall/private endpoint blocks client path | High |
| Private DNS issue | private endpoint approved but vault URI resolves public/NXDOMAIN | High |
| Secret version drift | app pins old version deleted/disabled or new value not picked up | Medium |
| Certificate expiry | certificate `expires` within threshold or expired | High |
| Key disabled/expired | key attributes disabled/expired + crypto failures | High |
| Purge protection expected behavior | purge blocked while protection enabled | High |

## 403 Forbidden Playbook

1. Determine data-plane vs management-plane operation.
2. Check `enableRbacAuthorization`.
3. For RBAC mode, list assignments for `{{user.principal_id}}` at vault and parent scopes.
4. For access policy mode, inspect vault access policies for object permissions.
5. Verify principal ID matches actual managed identity/service principal used by app.
6. Check firewall/private endpoint if authorization evidence is correct.

Safe actions:
- show vault access model;
- list role assignments/policies;
- show object metadata;
- query Activity Log.

Requires confirmation:
- add/remove role assignment;
- set/delete access policy;
- network ACL changes.

## Secret / Certificate / Key Lifecycle Playbooks

### Secret Not Found or Wrong Value

1. Check secret metadata and versions, not values.
2. Check deleted secret state if name is unavailable.
3. Correlate version changes with app deploy or config refresh.
4. Recommend app owner verify secret source and version pinning.

### Certificate Expiry

1. List certificate metadata and `expires` attributes.
2. Check issuer/renewal policy and recent failed operations.
3. Rank by days to expiry and production tags.
4. Recommend renewal/import owner actions with confirmation gates.

### Key Operation Failure

1. Check key enabled/expiry/not-before attributes.
2. Check caller role/policy for crypto operation.
3. Check key version pinning and rotation events.
4. Escalate cryptographic design to security owner.

## RCA Report Template

```text
Symptom: <what user observed>
Timeline: <start, peak, recent identity/network/object changes>
Access model: RBAC|AccessPolicy
Object evidence: <secret/key/cert metadata only, no values>
Identity evidence: <principal, roles/policies, tenant>
Network evidence: <public/private/firewall/DNS findings>
Likely root causes:
1. <cause> — Confidence: High|Medium|Low — Evidence: <evidence>
Safe next actions:
- <read-only diagnostic or owner check>
Actions requiring confirmation:
- <operation, impact, rollback/mitigation>
Security-owner review items:
- <permission/rotation/crypto/network action>
Escalation criteria:
- <when to involve Azure Support/security/network/app team>
```

## Escalation Criteria

Escalate when:
- secret/key/cert material may be compromised;
- purge/delete/permission changes affect production;
- network path requires VNet/DNS owner access;
- application uses an unknown identity;
- repeated 5xx/429 includes correlation IDs;
- cryptographic key design or rotation policy needs approval.
