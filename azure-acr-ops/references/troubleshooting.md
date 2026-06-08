# Azure Container Registry Troubleshooting and RCA

## Method: Evidence Before Conclusion

1. Confirm subscription, Resource Group, registry name, login server, SKU, network mode, and provisioning state.
2. Build incident timeline: symptom start, deployments, tag changes, RBAC changes, network changes, purge/retention events.
3. Verify image identity: repository, tag, digest, created/updated time.
4. Check identity path: AKS kubelet identity, managed identity, service principal, token, or admin user.
5. Check network path: public access, firewall, private endpoint, DNS, trusted services.
6. Correlate ACR logs, AKS events, Activity Log, and user-provided build/deploy events.
7. Rank root-cause candidates by evidence and confidence.

## Symptom Index

| Symptom | First Evidence | Likely Area |
|---------|----------------|-------------|
| `ImagePullBackOff` / `ErrImagePull` | AKS event + ACR repo/tag check | image existence, auth, network |
| `manifest unknown` | tag/digest lookup | wrong tag, deleted manifest, import lag |
| `unauthorized` / `authentication required` | RBAC/token/admin state | missing AcrPull, stale secret, token scope |
| Timeout pulling image | network rules, private endpoint, DNS | firewall/private DNS/VNet route |
| Push denied | AcrPush/RBAC, repository permissions | auth/scope map/quarantine |
| Pull latency high | registry logs, network path, image size | network, large layers, service issue |
| Repository growth | storage/repository history | retention gap, tag churn |
| Purge broke rollback | deletion timeline + deployments | retention/purge policy |

## Triage Commands

```bash
az acr show \
  --name "{{user.registry_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,loginServer:loginServer,sku:sku.name,state:provisioningState,admin:adminUserEnabled,publicNetworkAccess:publicNetworkAccess}" \
  --output json

az acr repository show-tags \
  --name "{{user.registry_name}}" \
  --repository "{{user.repository}}" \
  --detail \
  --output json

az monitor activity-log list \
  --resource-group "{{user.resource_group}}" \
  --resource-id "{{output.registry_id}}" \
  --offset "{{user.analysis_window}}" \
  --output json
```

For AKS pull issues, request pod event excerpt from `azure-aks-ops` or user-provided `kubectl describe pod` output; do not guess kubelet identity.

## Root Cause Rules

| Rule | Evidence Pattern | Confidence |
|------|------------------|------------|
| Image tag missing | pod references tag not present in ACR | High |
| Digest mismatch | deployed digest differs from ACR manifest | High |
| Missing `AcrPull` | identity lacks AcrPull on registry scope + unauthorized pull | High |
| Stale pull secret | secret/token rotation event precedes auth failures | High |
| Admin user disabled | clients use admin credentials while admin disabled | High |
| Firewall deny | public endpoint used + client/AKS egress not allowed | High |
| Private DNS issue | private endpoint approved but login server resolves public/NXDOMAIN | High |
| Tag overwritten | tag updated near deployment + digest changed | Medium; High with deployment evidence |
| Purge/retention deleted image | delete/purge event precedes not-found errors | High |
| Large image/network pressure | pull latency high + large image/layers + normal auth | Medium |
| Registry throttling/service issue | 429/5xx across many clients + correlation IDs | Medium until Azure Support confirms |

## AKS Image Pull Playbook

1. Capture image reference: `{{output.login_server}}/{{user.repository}}:{{user.tag}}` or digest.
2. Verify repository/tag/digest exists in ACR.
3. Identify AKS pull identity and check `AcrPull` at registry scope.
4. Check registry network mode and whether cluster egress/private path is allowed.
5. Correlate failures with Activity Log: RBAC, firewall, private endpoint, purge, tag delete/import.
6. Return ACR-side conclusion and delegate cluster internals to `azure-aks-ops`.

Safe actions:
- list repository/tag/manifest;
- show registry/network config;
- check Activity Log;
- report required RBAC assignment.

Requires confirmation:
- assign/remove RBAC;
- enable admin user;
- modify firewall/private endpoint;
- import/overwrite production tag.

## Repository Growth / Cleanup Playbook

1. List repositories and tag metadata.
2. Identify high-churn repositories and stale tags.
3. Check retention/purge policy and recent delete events.
4. Recommend cleanup rules with protected patterns for production tags/digests.

Never purge automatically. Purge plans must include sample matches, protected tags, rollback impact, and explicit confirmation.

## RCA Report Template

```text
Symptom: <what user observed>
Timeline: <start, peak, recent registry/RBAC/network/image changes>
Image evidence: <repository, tag, digest, existence, timestamps>
Identity evidence: <principal/identity, AcrPull/token/admin state>
Network evidence: <public/private/firewall/DNS findings>
Likely root causes:
1. <cause> — Confidence: High|Medium|Low — Evidence: <evidence>
Safe next actions:
- <read-only diagnostic or owner check>
Actions requiring confirmation:
- <operation, impact, rollback/mitigation>
Owner-review items:
- <AKS/build/network/security action>
Escalation criteria:
- <when to involve Azure Support/security/network/app team>
```

## Escalation Criteria

Escalate when:
- repeated 5xx/429 includes correlation IDs;
- AKS identity or node-level evidence is required;
- network path requires VNet/DNS owner access;
- purge/delete may have removed production rollback images;
- credential/token compromise is suspected.
