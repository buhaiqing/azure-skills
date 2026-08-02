# Integration Setup (Azure Front Door Skills)

## Environment Setup

Azure CLI and Azure SDK require authentication via Azure AD. Use **Service Principal** for automation.

### Install Azure CLI (One-time per machine)

```bash
# macOS
brew install azure-cli

# Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
# Download from: https://aka.ms/installazurecliwindows
```

### Install Azure SDK for Python

```bash
# Core packages
pip install azure-identity azure-mgmt-resource

# CDN management (required for Front Door skills)
pip install azure-mgmt-cdn
```

### Verify Installation

```bash
az --version
python -c "from azure.identity import DefaultAzureCredential; from azure.mgmt.cdn import CdnManagementClient; print('OK')"
```

## Credential Configuration

### Method A: Service Principal (Recommended for Automation)

**Create Service Principal**:
```bash
az ad sp create-for-rbac \
  --name "my-automation-sp" \
  --role "CDN Profile Contributor" \
  --scopes "/subscriptions/{{subscription-id}}" \
  --output json
```

**Store credentials as environment variables**:
```bash
export AZURE_SUBSCRIPTION_ID="{{subscription-id}}"
export AZURE_TENANT_ID="{{tenant-id}}"
export AZURE_CLIENT_ID="{{app-id}}"
export AZURE_CLIENT_SECRET="{{password}}"
```

### Method B: Azure CLI Login (Interactive)

```bash
az login --subscription "{{subscription-id}}"
az account show --output json
```

## Required Permissions

| Operation | Required RBAC Role |
|-----------|-------------------|
| Create Front Door profile | CDN Profile Contributor |
| Manage endpoints | CDN Profile Contributor |
| Configure WAF (Premium) | CDN Profile Contributor + WAF Policy Contributor |
| Manage custom domains | CDN Profile Contributor |

## Front Door Endpoint Naming

Front Door endpoint names must be **globally unique**:
- Becomes part of DNS name: `{{endpoint-name}}-{{hash}}.azurefd.net`
- Cannot conflict with any existing Front Door endpoint
- Use descriptive names with organization prefix

## Verify Credentials

```bash
az account show --output json
```

## Project-based Setup (pyproject.toml)

```toml
[project]
name = "azure-frontdoor-ops"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "azure-identity>=1.10.0",
    "azure-mgmt-resource>=21.0.0",
    "azure-mgmt-cdn>=12.0.0",
]
```

## Safety Rules

- **NEVER** commit `.env` files
- **NEVER** write credentials into Skill documents
- Generated Skills use `{{env.*}}` placeholders only
- Front Door endpoint names must be globally unique

## Full Command Reference (Azure CLI)

All operations use `az afd` (Front Door Standard/Premium). The deprecated `az network front-door` MUST NOT be used.

### Create Front Door Profile (full topology)

```bash
# Create Front Door Standard/Premium profile
az afd profile create \
  --profile-name "{{user.fd_name}}" \
  --resource-group "{{user.resource_group}}" \
  --sku Standard_AzureFrontDoor \
  --output json

# Create endpoint
az afd endpoint create \
  --endpoint-name "{{user.endpoint_name}}" \
  --profile-name "{{user.fd_name}}" \
  --resource-group "{{user.resource_group}}" \
  --enabled-state Enabled \
  --output json

# Create origin group (backend pool)
az afd origin-group create \
  --origin-group-name "origin-group" \
  --profile-name "{{user.fd_name}}" \
  --resource-group "{{user.resource_group}}" \
  --probe-name "health-probe" \
  --output json

# Create health probe
az afd probe create \
  --probe-name "health-probe" \
  --profile-name "{{user.fd_name}}" \
  --resource-group "{{user.resource_group}}" \
  --probe-interval-in-seconds 60 \
  --probe-path "/" \
  --probe-protocol Https \
  --output json

# Create origin (backend server)
az afd origin create \
  --origin-name "origin-1" \
  --origin-group-name "origin-group" \
  --profile-name "{{user.fd_name}}" \
  --resource-group "{{user.resource_group}}" \
  --origin-host-name "{{user.backend_host}}" \
  --origin-host-header "{{user.backend_host}}" \
  --http-port 80 \
  --https-port 443 \
  --priority 1 \
  --weight 1000 \
  --output json

# Create route (routing rule)
az afd route create \
  --route-name "route" \
  --endpoint-name "{{user.endpoint_name}}" \
  --profile-name "{{user.fd_name}}" \
  --resource-group "{{user.resource_group}}" \
  --origin-group "origin-group" \
  --patterns-to-match "/*" \
  --supported-protocols Http Https \
  --forward-protocol Https \
  --output json
```

### Validate (after create)

```bash
az afd profile show --profile-name "{{user.fd_name}}" --resource-group "{{user.resource_group}}" --output json
az afd endpoint show --endpoint-name "{{user.endpoint_name}}" --profile-name "{{user.fd_name}}" --resource-group "{{user.resource_group}}" --output json
# Check provisioning state: should be "Succeeded"
# Endpoint hostname: `{{endpoint_name}}-{{hash}}.azurefd.net`
```

### Add Custom Domain

```bash
az afd custom-domain create \
  --custom-domain-name "{{user.custom_domain_name}}" \
  --profile-name "{{user.fd_name}}" \
  --resource-group "{{user.resource_group}}" \
  --host-name "{{user.custom_domain}}" \
  --certificate-type ManagedCertificate \
  --minimum-tls-version TLS12 \
  --output json

az afd route update \
  --route-name "route" \
  --endpoint-name "{{user.endpoint_name}}" \
  --profile-name "{{user.fd_name}}" \
  --resource-group "{{user.resource_group}}" \
  --custom-domains "{{user.custom_domain_name}}" \
  --output json
```

### Enable WAF Policy

```bash
az network front-door waf-policy create \
  --name "{{user.waf_policy_name}}" \
  --resource-group "{{user.resource_group}}" \
  --mode Prevention \
  --output json

az afd security-policy create \
  --security-policy-name "waf-policy" \
  --profile-name "{{user.fd_name}}" \
  --resource-group "{{user.resource_group}}" \
  --waf-policy "{{user.waf_policy_id}}" \
  --output json
```

### Delete Front Door Profile (requires explicit confirmation — see SKILL.md Safety Gate)

```bash
az afd profile show --profile-name "{{user.fd_name}}" --resource-group "{{user.resource_group}}" --output json
az afd profile delete --profile-name "{{user.fd_name}}" --resource-group "{{user.resource_group}}" --output json
```

### Azure SDK (Python) Fallback — Create Profile

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.cdn import CdnManagementClient
import os

client = CdnManagementClient(DefaultAzureCredential(), os.environ.get('AZURE_SUBSCRIPTION_ID'))
# client bootstrap: see ../../../azure-skill-generator/references/azure-sdk-usage.md#common-client-bootstrap

profile = client.profiles.begin_create(
    resource_group_name='{{user.resource_group}}',
    profile_name='{{user.fd_name}}',
    profile={
        'location': 'Global',
        'sku': {'name': 'Standard_AzureFrontDoor'},
        'origin_response_timeout_seconds': 30
    }
).result()
```

### Recovery Decision Table

| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| QuotaExceeded | HALT; request quota increase |
| NameNotAvailable | HALT; endpoint name must be globally unique |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |