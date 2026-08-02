# Azure SDK Usage Reference (Python)

## Overview

Azure SDK for Python is the official SDK. Use as **fallback** when Azure CLI fails after 3 retries.

## Credential Options

| Method | Description | Use Case |
|--------|-------------|----------|
| **DefaultAzureCredential** | Auto-detects from env, CLI, Managed Identity | Recommended for flexibility |
| **EnvironmentCredential** | Explicit env vars only | CI/CD pipelines |
| **ServicePrincipalCredential** | Explicit client ID/secret | Legacy; prefer DefaultAzureCredential |

## Common Client Bootstrap (canonical source)

**All `azure-*-ops/references/integration.md` MUST link here instead of inlining.**
Standard 4-line pattern:

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.[service] import [ServiceMgmtClient]
import os

credential = DefaultAzureCredential()
client = [ServiceMgmtClient](credential, os.environ.get('AZURE_SUBSCRIPTION_ID'))
```

| Variant | When | One-liner form |
|---------|------|----------------|
| `os.environ["..."]` (no default) | Required at import time | `os.environ["AZURE_SUBSCRIPTION_ID"]` |
| `os.environ.get('...')` (with default) | Optional in tests | `os.environ.get('AZURE_SUBSCRIPTION_ID')` |
| `subscription_id=...` as named kwarg | Always; matches SDK signature | `ComputeManagementClient(credential, subscription_id=...)` |

**In `integration.md`, use this one-liner + link, never re-inline the 4-line block:**

```python
from azure.identity import DefaultAzureCredential
client = ComputeManagementClient(DefaultAzureCredential(), os.environ.get('AZURE_SUBSCRIPTION_ID'))
# bootstrap rationale + verify: see azure-sdk-usage.md#common-client-bootstrap
```

## Required Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_SUBSCRIPTION_ID` | Azure subscription GUID |
| `AZURE_TENANT_ID` | Azure AD tenant GUID |
| `AZURE_CLIENT_ID` | Service Principal app ID |
| `AZURE_CLIENT_SECRET` | Service Principal secret |

## Operation Patterns

> Assumes `client` already created via [Common Client Bootstrap](#common-client-bootstrap). Re-import the credential/client only if operating in a fresh interpreter (tests, notebooks).

### Create Operation (Long Running)

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.[service] import [ServiceMgmtClient]
# bootstrap: see [Common Client Bootstrap](#common-client-bootstrap)
client = [ServiceMgmtClient](DefaultAzureCredential(), subscription_id='{{env.AZURE_SUBSCRIPTION_ID}}')

poller = client.[resources].begin_create_or_update(
    resource_group_name='{{user.resource_group}}',
    resource_name='{{user.resource_name}}',
    parameters={
        'location': '{{user.location}}',
        'tags': {'Environment': 'production'},
    }
)
result = poller.result()  # blocking; raises on Failed
resource_id = result.id
```

### Get Operation

```python
response = client.[resources].get(
    resource_group_name='{{user.resource_group}}',
    resource_name='{{user.resource_name}}'
)

# Common response structure
# response.name, response.id, response.location, response.properties
```

### List Operation (Pagination)

```python
# List within resource group
resources = client.[resources].list_by_resource_group(
    resource_group_name='{{user.resource_group}}'
)

for resource in resources:
    print(resource.name, resource.location)

# List across subscription
all_resources = client.[resources].list()
for resource in all_resources:
    print(resource.name)
```

### Delete Operation (Long Running)

```python
poller = client.[resources].begin_delete(
    resource_group_name='{{user.resource_group}}',
    resource_name='{{user.resource_name}}'
)

# Wait for deletion completion
poller.wait()  # Non-blocking wait
# OR
poller.result()  # Blocking wait
```

## Error Handling Pattern

```python
from azure.core.exceptions import HttpResponseError, AzureError

try:
    poller = client.[resources].begin_create_or_update(...)
    result = poller.result()
except HttpResponseError as e:
    error_code = e.error.code if e.error else 'Unknown'
    error_msg = e.error.message if e.error else str(e)
    
    if error_code == 'InvalidParameter':
        # Fix and retry once
        pass
    elif error_code == 'QuotaExceeded':
        # HALT
        raise RuntimeError(f"Quota exceeded: {error_msg}")
    elif error_code == 'Throttling':
        # Retry with backoff
        pass
    elif error_code == 'ResourceNotFound':
        # HALT; resource doesn't exist
        raise RuntimeError(f"Resource not found: {error_msg}")
    else:
        raise
except AzureError as e:
    # Connection/timeout issues
    # Retry up to 3 times
    raise
```

## Common Error Codes

| Error Code | HTTP | Action |
|------------|------|--------|
| InvalidParameter | 400 | Fix args; retry once |
| AccessDenied | 403 | HALT; check RBAC permissions |
| ResourceNotFound | 404 | HALT; resource doesn't exist |
| Conflict | 409 | Check state; retry once |
| QuotaExceeded | 400/402 | HALT; request increase |
| Throttling | 429 | Backoff; retry 3x |
| InternalError | 500 | Retry 3x; then HALT |
| ServiceUnavailable | 503 | Retry 3x; then HALT |

## Retry Strategy Implementation

```python
import time
from azure.core.exceptions import HttpResponseError

def retry_operation(func, max_retries=3, backoff_base=2):
    """
    Retry with exponential backoff for transient errors.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except HttpResponseError as e:
            error_code = e.error.code if e.error else 'Unknown'
            
            # Non-retryable errors
            if error_code in ['InvalidParameter', 'AccessDenied', 'ResourceNotFound']:
                raise
            
            # Retryable errors
            if attempt < max_retries - 1:
                time.sleep(backoff_base ** attempt)
            else:
                raise
```

## Polling Pattern (Long Running Operations)

```python
import time

def wait_for_lro(poller, max_wait=300, interval=5):
    """
    Wait for Long Running Operation completion.
    """
    while not poller.done():
        time.sleep(interval)
        if time.time() - start_time > max_wait:
            raise TimeoutError("LRO timeout")
    
    result = poller.result()
    
    # Check provisioning state
    if result.properties.provisioning_state == 'Failed':
        raise RuntimeError(f"Resource creation failed")
    
    return result

# Usage
poller = client.[resources].begin_create_or_update(...)
result = wait_for_lro(poller, max_wait=600)
```

## Service-Specific Notes (Template)

Replace these placeholders for each service:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `[service]` | Azure service name | `compute`, `storage`, `network` |
| `[ServiceMgmtClient]` | Management client class | `ComputeManagementClient`, `StorageManagementClient` |
| `[resources]` | Resource operations object | `virtual_machines`, `storage_accounts` |
| `[Resource]` | Resource type | `VirtualMachine`, `StorageAccount` |

## Azure SDK vs AWS boto3 Comparison

| Aspect | Azure SDK | boto3 |
|--------|-----------|-------|
| Credential | `DefaultAzureCredential` | boto3 auto-detects |
| Async ops | LRO poller pattern | Paginator or waiters |
| Output | Python objects | Python dict |
| Pagination | Iterator objects | Paginator or manual |
| Best for | Integration tests, complex logic | Quick ops, scripts |

## Package Installation

```bash
# Core identity package
pip install azure-identity

# Service-specific management packages
pip install azure-mgmt-compute
pip install azure-mgmt-storage
pip install azure-mgmt-network
pip install azure-mgmt-resource
```

Or using pyproject.toml:

```toml
[project]
dependencies = [
    "azure-identity>=1.10.0",
    "azure-mgmt-resource>=21.0.0",
    # Add service-specific packages
]
```