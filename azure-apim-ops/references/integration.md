# Integration Setup (Azure API Management Skills)

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

# API Management management (required for APIM skills)
pip install azure-mgmt-apimanagement
```

### Verify Installation

```bash
az --version
python -c "from azure.identity import DefaultAzureCredential; from azure.mgmt.apimanagement import ApiManagementClient; print('OK')"
```

## Credential Configuration

### Method A: Service Principal (Recommended for Automation)

**Create Service Principal**:
```bash
az ad sp create-for-rbac \
  --name "my-apim-automation-sp" \
  --role "API Management Service Contributor" \
  --scopes "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --output json
```

**Store credentials as environment variables**:
```bash
export AZURE_SUBSCRIPTION_ID="{{env.AZURE_SUBSCRIPTION_ID}}"
export AZURE_TENANT_ID="{{env.AZURE_TENANT_ID}}"
export AZURE_CLIENT_ID="{{env.AZURE_CLIENT_ID}}"
export AZURE_CLIENT_SECRET="{{env.AZURE_CLIENT_SECRET}}"
```

### Method B: Azure CLI Login (Interactive)

```bash
az login --subscription "{{env.AZURE_SUBSCRIPTION_ID}}"
az account show --output json
```

## Required Permissions

| Operation | Required RBAC Role |
|-----------|-------------------|
| Create / Update / Delete APIM | API Management Service Contributor |
| Read APIM | API Management Service Reader |
| Apply policies (global / api / product) | API Management Service Contributor |
| Manage subscriptions & keys | API Management Service Contributor |
| Apply RBAC on APIM | Owner or User Access Administrator |

## CLI vs SDK Coverage Summary

`az apim` is a **partial** CLI — many important operations are SDK-only:

| Group | CLI Command | SDK Class |
|-------|-------------|-----------|
| Service | `az apim create/show/list/delete/update/wait/check-name/backup/restore` | `ApiManagementServiceOperations` |
| API | `az apim api create/show/list/delete/update/import/export/wait` | `ApiOperations` |
| API Operation | `az apim api operation create/show/list/update/delete` | `ApiOperationOperations` |
| API Revision | `az apim api revision create/list` | `ApiRevisionOperations` |
| API Release | `az apim api release create/show/list/update/delete` | `ApiReleaseOperations` |
| API Version Set | `az apim api versionset create/show/list/update/delete` | `ApiVersionSetOperations` |
| API Schema | `az apim api schema create/show/list/delete/get-etag/wait` | `ApiSchemaOperations` |
| Product | `az apim product create/show/list/update/delete/wait` | `ProductOperations` |
| Product ↔ API | `az apim product api add/check/delete/list` | `ProductApiOperations` |
| Named Value | `az apim nv create/show/list/delete/show-secret/update/wait` | `NamedValueOperations` |
| Backend | `az apim backend create/show/list/update/delete` | `BackendOperations` |
| Soft-deleted | `az apim deletedservice list/show/purge` | `DeletedServicesOperations` |
| **Subscription** | ❌ **no CLI** | `SubscriptionOperations` |
| **API Policy** | ❌ **no CLI** | `ApiPolicyOperations` |
| **Product Policy** | ❌ **no CLI** | `ProductPolicyOperations` |
| **Global Policy** | ❌ **no CLI** | `PolicyOperations` |
| GraphQL Resolver | `az apim graphql resolver create/show/list/delete` | `GraphQLApiResolverOperations` |
| GraphQL Resolver Policy | `az apim graphql resolver policy create/show/list/delete` | `GraphQLApiResolverPolicyOperations` |

## SDK Bootstrap Pattern

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.apimanagement import ApiManagementClient
import os

client = ApiManagementClient(DefaultAzureCredential(), os.environ.get('AZURE_SUBSCRIPTION_ID'))
# client bootstrap: see ../../../azure-skill-generator/references/azure-sdk-usage.md#common-client-bootstrap

# Verify subscription access
sub = client.api_management_service.list_by_resource_group(
    resource_group_name='{{user.resource_group}}'
)
for apim in sub:
    print(apim.name, apim.location)
```

## SDK Operation Patterns

### Create APIM Service (Long Running)

```python
from azure.mgmt.apimanagement import ApiManagementClient
from azure.mgmt.apimanagement.models import (
    ApiManagementServiceResource,
    ApiManagementServiceSkuProperties,
)

poller = client.api_management_service.begin_create_or_update(
    resource_group_name='{{user.resource_group}}',
    service_name='{{user.apim_name}}',
    parameters=ApiManagementServiceResource(
        location='{{user.location}}',
        sku=ApiManagementServiceSkuProperties(
            name='{{user.apim_sku}}',  # SkuType enum
            capacity=1,
        ),
        publisher_email='{{user.publisher_email}}',
        publisher_name='{{user.publisher_name}}',
    ),
)
apim = poller.result()  # LRO: 5-45 min for non-Consumption SKU
print(f"Gateway URL: {apim.gateway_url}")
```

### Create API (Long Running)

```python
from azure.mgmt.apimanagement.models import ApiCreateOrUpdateParameter, Protocol

api = client.api.begin_create_or_update(
    resource_group_name='{{user.resource_group}}',
    service_name='{{user.apim_name}}',
    api_id='{{user.api_id}}',
    parameters=ApiCreateOrUpdateParameter(
        display_name='{{user.api_display_name}}',
        path='/myapi',
        protocols=[Protocol.HTTPS],
        service_url='https://my-backend.example.com',
        subscription_required=True,
    ),
).result()
```

### Create Product

```python
from azure.mgmt.apimanagement.models import ProductContract, ProductState

product = client.product.create_or_update(
    resource_group_name='{{user.resource_group}}',
    service_name='{{user.apim_name}}',
    product_id='{{user.product_id}}',
    parameters=ProductContract(
        display_name='{{user.product_display_name}}',
        description='{{user.product_description}}',
        state=ProductState.PUBLISHED,
        subscription_required=True,
        approval_required=False,
    ),
)
```

### Add API to Product

```python
client.product_api.create_or_update(
    resource_group_name='{{user.resource_group}}',
    service_name='{{user.apim_name}}',
    product_id='{{user.product_id}}',
    api_id='{{user.api_id}}',
)
```

### Create Subscription (SDK ONLY — no CLI)

```python
from azure.mgmt.apimanagement.models import (
    SubscriptionCreateParameters,
    SubscriptionState,
)

sub = client.subscription.create_or_update(
    resource_group_name='{{user.resource_group}}',
    service_name='{{user.apim_name}}',
    sid='{{user.subscription_id}}',
    parameters=SubscriptionCreateParameters(
        scope=f"/products/{{user.product_id}}",
        display_name='{{user.subscription_display_name}}',
        state=SubscriptionState.ACTIVE,
    ),
)

# Get primary/secondary keys — sensitive; do NOT log
secrets = client.subscription.list_secrets(
    resource_group_name='{{user.resource_group}}',
    service_name='{{user.apim_name}}',
    sid='{{user.subscription_id}}',
)
# secrets.primary_key, secrets.secondary_key — handle securely
```

### Regenerate Subscription Key (SDK ONLY — no CLI)

```python
# WARNING: Existing clients using the current key will fail until updated
client.subscription.regenerate_primary_key(
    resource_group_name='{{user.resource_group}}',
    service_name='{{user.apim_name}}',
    sid='{{user.subscription_id}}',
)
```

### Apply Global Policy (SDK ONLY — no CLI)

```python
from azure.mgmt.apimanagement.models import (
    PolicyContract,
    PolicyContentFormat,
    PolicyIdName,
)

policy_xml = """<policies>
  <inbound>
    <rate-limit calls="100" renewal-period="60" />
    <base />
  </inbound>
  <backend><base /></backend>
  <outbound><base /></outbound>
  <on-error><base /></on-error>
</policies>"""

client.policy.create_or_update(
    resource_group_name='{{user.resource_group}}',
    service_name='{{user.apim_name}}',
    policy_id=PolicyIdName.POLICY,
    parameters=PolicyContract(
        value=policy_xml,
        format=PolicyContentFormat.XML,
    ),
)
```

### Apply API Policy (SDK ONLY — no CLI)

```python
client.api_policy.create_or_update(
    resource_group_name='{{user.resource_group}}',
    service_name='{{user.apim_name}}',
    api_id='{{user.api_id}}',
    policy_id=PolicyIdName.POLICY,
    parameters=PolicyContract(
        value=policy_xml,
        format=PolicyContentFormat.XML,
    ),
)
```

### Apply Product Policy (SDK ONLY — no CLI)

```python
client.product_policy.create_or_update(
    resource_group_name='{{user.resource_group}}',
    service_name='{{user.apim_name}}',
    product_id='{{user.product_id}}',
    policy_id=PolicyIdName.POLICY,
    parameters=PolicyContract(
        value=policy_xml,
        format=PolicyContentFormat.XML,
    ),
)
```

## Error Handling

```python
from azure.core.exceptions import HttpResponseError

try:
    poller = client.api_management_service.begin_create_or_update(...)
    apim = poller.result()
except HttpResponseError as e:
    error_code = e.error.code if e.error else 'Unknown'
    error_msg = e.error.message if e.error else str(e)

    if error_code in ('InvalidParameter', 'InvalidPublisherEmail'):
        # Fix args; retry once
        raise
    elif error_code == 'CheckNameNotAvailable':
        # HALT; name conflict
        raise RuntimeError(f"APIM name conflict: {error_msg}")
    elif error_code == 'QuotaExceeded':
        # HALT; user requests quota increase
        raise RuntimeError(f"Quota exceeded: {error_msg}")
    elif error_code == 'ThrottlingException':
        # Backoff; retry 3x
        raise
    else:
        raise
```

## Polling Pattern (LRO)

```python
import time

def wait_for_apim(poller, max_wait=3000, interval=10):
    """Wait for APIM LRO completion. Non-Consumption SKU can take 5-45 min."""
    start = time.time()
    while not poller.done():
        time.sleep(interval)
        elapsed = time.time() - start
        if elapsed > max_wait:
            raise TimeoutError(f"APIM LRO timeout after {max_wait}s")
        print(f"Waiting... {elapsed:.0f}s elapsed")
    return poller.result()

apim = wait_for_apim(poller, max_wait=3000)
```

## Project-based Setup (pyproject.toml)

```toml
[project]
name = "azure-apim-ops"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "azure-identity>=1.10.0",
    "azure-mgmt-resource>=21.0.0",
    "azure-mgmt-apimanagement>=5.0.0",
]
```

## Verify Credentials

```bash
az account show --output json
```

## Safety Rules

- **NEVER** commit `.env` files
- **NEVER** write credentials into Skill documents
- **NEVER** log subscription primary/secondary keys — they are sensitive credentials
- **NEVER** log Policy XML in full when it contains `value=` with secrets (connection strings, JWT signing keys, AAD client secrets) — mask or omit
- Generated Skills use `{{env.*}}` placeholders only