# Azure Key Vault Core Concepts

## Resource Identity

Use full resource IDs in reports and traces:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.KeyVault/vaults/{{user.vault_name}}
```

Data-plane object URIs use the vault URI:

```text
{{output.vault_uri}}secrets/{{user.secret_name}}
{{output.vault_uri}}keys/{{user.key_name}}
{{output.vault_uri}}certificates/{{user.certificate_name}}
```

Never print secret values.

## Key Concepts

| Concept | Meaning | Operational Impact |
|---------|---------|--------------------|
| Vault | Container for secrets, keys, certificates | Main resource controlled by `az keyvault` |
| Secret | Versioned opaque value | Values are sensitive; metadata is safe to inspect |
| Key | Cryptographic key | Rotation/delete/disable can break encryption/signing |
| Certificate | Certificate object with policy and secret backing | Expiry and issuer state affect apps |
| RBAC mode | Azure RBAC authorizes data-plane operations | Check role assignments on vault/scope |
| Access policy mode | Vault-local access policies authorize data plane | Check policies and object permissions |
| Soft-delete | Deleted vault/object remains recoverable | Affects name reuse and recovery |
| Purge protection | Prevents permanent purge until retention expires | Critical safety control |
| Firewall rules | Public endpoint allowlist | Misconfig causes 403/network failures |
| Private endpoint | Private access to data plane | Requires Private DNS and VNet routing |
| Managed identity | Common app auth path | Principal object ID and roles/policies must match |

## Access Models

| Mode | Indicator | Diagnostic Path |
|------|-----------|-----------------|
| Azure RBAC | `enableRbacAuthorization=true` | Check role assignments: Key Vault Secrets User, Key Vault Crypto User, etc. |
| Access Policy | `enableRbacAuthorization=false` | Check `accessPolicies` and per-object permissions |

Do not mix assumptions. Identify the mode before diagnosing 403.

## Common Roles

| Role | Typical Capability |
|------|--------------------|
| Key Vault Reader | Read vault metadata, not secret values |
| Key Vault Secrets User | Read secret values through data plane |
| Key Vault Secrets Officer | Manage secrets |
| Key Vault Crypto User | Use keys for cryptographic operations |
| Key Vault Certificates Officer | Manage certificates |
| Key Vault Administrator | Broad data-plane management; use sparingly |

## Delegation Boundaries

| Need | Delegate |
|------|----------|
| Generic RBAC audit, locks, policy-only work | `azure-audit-ops` |
| Generic Monitor KQL/alerts | `azure-monitor-ops` |
| Cost analysis | `azure-cost-ops` |
| Deep VNet/Private DNS design | network owner after this skill provides entry diagnostics |
| App code secret-loading changes | app owner |
| Cryptographic architecture | security owner |
