# Azure Key Vault Integration and Commands

## Required Tools

```bash
az version --output json
az account show --output json
az provider show --namespace Microsoft.KeyVault --output json
```

If `Microsoft.KeyVault` is not registered, HALT and ask for approval before registration:

```bash
az provider register --namespace Microsoft.KeyVault --output json
```

## Required RBAC

| Operation | Minimum Role |
|-----------|--------------|
| Read vault metadata | Reader |
| Read secret metadata | Key Vault Reader or appropriate access policy |
| Read secret value | Key Vault Secrets User or access policy; do not print value |
| Manage secrets | Key Vault Secrets Officer or access policy |
| Manage keys | Key Vault Crypto Officer/Key Vault Administrator or access policy |
| Manage certificates | Key Vault Certificates Officer or access policy |
| Vault create/update/delete | Contributor on resource scope |
| Role assignment changes | User Access Administrator or Owner; prefer delegate to `azure-audit-ops` |

## Pre-flight Checklist

```bash
az account show --output json
az group show --name "{{user.resource_group}}" --output json
az account list-locations --query "[?name=='{{user.location}}']" --output json
az provider show --namespace Microsoft.KeyVault --query "registrationState" --output json
```

For existing vault:

```bash
az keyvault show \
  --name "{{user.vault_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

## Azure CLI Primary Path

### Vault List and Show

```bash
az keyvault list \
  --resource-group "{{user.resource_group}}" \
  --output json

az keyvault show \
  --name "{{user.vault_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,uri:properties.vaultUri,rbac:properties.enableRbacAuthorization,purgeProtection:properties.enablePurgeProtection,publicNetworkAccess:properties.publicNetworkAccess}" \
  --output json
```

### Create Vault

```bash
az keyvault create \
  --name "{{user.vault_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --enable-rbac-authorization true \
  --enable-purge-protection true \
  --output json
```

### Secret Metadata and Safe Set Pattern

```bash
az keyvault secret list \
  --vault-name "{{user.vault_name}}" \
  --output json

az keyvault secret show \
  --vault-name "{{user.vault_name}}" \
  --name "{{user.secret_name}}" \
  --query "{id:id,attributes:attributes,tags:tags,contentType:contentType}" \
  --output json
```

Do not print secret values. For set/overwrite, require confirmation and instruct the user to use a secure local source:

```bash
az keyvault secret set \
  --vault-name "{{user.vault_name}}" \
  --name "{{user.secret_name}}" \
  --value "<read-from-secure-local-source>" \
  --output json
```

### Key and Certificate Metadata

```bash
az keyvault key list \
  --vault-name "{{user.vault_name}}" \
  --output json

az keyvault certificate list \
  --vault-name "{{user.vault_name}}" \
  --output json

az keyvault certificate show \
  --vault-name "{{user.vault_name}}" \
  --name "{{user.certificate_name}}" \
  --query "{id:id,attributes:attributes,policy:policy,tags:tags}" \
  --output json
```

### Access Model Diagnostics

```bash
az keyvault show \
  --name "{{user.vault_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "properties.enableRbacAuthorization" \
  --output json

az role assignment list \
  --scope "{{output.vault_id}}" \
  --assignee "{{user.principal_id}}" \
  --output json
```

Access policy mode:

```bash
az keyvault show \
  --name "{{user.vault_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "properties.accessPolicies" \
  --output json
```

### Delete / Recover / Purge

```bash
az keyvault show \
  --name "{{user.vault_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# After explicit confirmation:
az keyvault delete \
  --name "{{user.vault_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

Purge is permanent and may be blocked by purge protection. Require explicit confirmation and security-owner approval.

## Azure SDK Fallback

Use SDK only after CLI transient failures are retried up to 3x.

```python
import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.keyvault import KeyVaultManagementClient

client = KeyVaultManagementClient(DefaultAzureCredential(), os.environ["AZURE_SUBSCRIPTION_ID"])
# client bootstrap: see ../../../azure-skill-generator/references/azure-sdk-usage.md#common-client-bootstrap

vault = client.vaults.get(
    resource_group_name="{{user.resource_group}}",
    vault_name="{{user.vault_name}}",
)
print(vault.id)
```

Data-plane metadata example:

```python
from azure.keyvault.secrets import SecretClient

secret_client = SecretClient(vault_url="{{output.vault_uri}}", credential=credential)
secret_properties = secret_client.get_secret("{{user.secret_name}}").properties
print(secret_properties.id)
```

Do not print `get_secret(...).value`.

## Polling

| Operation | Poll Interval | Max Wait |
|-----------|---------------|----------|
| create/update/delete vault | 30s | 30m |
| recover vault/object | 30s | 30m |
| purge vault/object | 30s | 30m |
| object metadata operations | 10s | 5m |
| network update | 30s | 20m |

On timeout, do not repeat mutation. Re-read state and report uncertainty.
