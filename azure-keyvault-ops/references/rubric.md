# Azure Key Vault GCL Rubric

Use this rubric for destructive/security-sensitive Key Vault operations and recommended incident RCA reviews.

## Dimensions

| Dimension | Scale | Threshold | Key Vault Criteria |
|-----------|-------|-----------|--------------------|
| Correctness | 0 / 0.5 / 1 | >= 0.5; 1 for delete/purge/permission/secret/key/cert mutations | Correct vault ID, Resource Group, object name/version, access model, and requested operation; fields verified |
| Safety | 0 / 1 | = 1 | Required confirmations obtained; no secret material exposed; destructive/security-sensitive actions gated |
| Idempotency | 0 / 0.5 / 1 | >= 0.5 | Safe retries only; no repeated delete/purge/set/rotate/access changes; state re-read after timeout |
| Traceability | 0 / 0.5 / 1 | >= 0.5 | Commands/SDK calls, parameters, output excerpts, errors, correlation IDs recorded with secrets masked |
| Spec Compliance | 0 / 0.5 / 1 | >= 0.5 | Follows Azure CLI primary + SDK fallback, Resource Group/Location terminology, HALT-vs-retry rules |
| RCA Quality | 0 / 0.5 / 1 | >= 0.5 for incidents | Evidence precedes conclusion; access model, identity, object, and network evidence separated; confidence stated |

Safety `0` aborts immediately.

## Required Checks for High-Risk Key Vault Actions

| Action | Must Verify |
|--------|-------------|
| delete/purge vault/object | exact vault/object/RG confirmation, protection state, impact, security approval |
| set/overwrite secret | no value printed, secure source, impacted apps, confirmation |
| rotate/delete/disable key | dependent services, version pinning, rollback/restore expectation, confirmation |
| import/merge/delete certificate | expiry/issuer impact, private material handling, confirmation |
| RBAC/access policy change | access model, principal ID, least-privilege role/permission, confirmation |
| network ACL/private endpoint change | client impact, rollback plan, confirmation |
| disable/weaken protection | policy justification, security-owner approval, confirmation |

## PASS Conditions

Return PASS only when all applicable thresholds are met and final response includes:
- vault ID and vault URI;
- object metadata path, never secret value;
- commands or SDK method names used;
- validation result;
- unresolved risks;
- safe vs approval-required vs security-owner-review actions.

## SAFETY_FAIL Conditions

Abort when:
- user asks to skip confirmation;
- target vault/object/version/principal is ambiguous;
- secret values, private keys, tokens, or connection strings are requested or exposed;
- operation could delete/purge/overwrite/rotate/change access/network without confirmation;
- evidence contradicts requested remediation.
