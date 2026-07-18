# Integration Setup (Azure Traffic Manager Skills)

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

# Traffic Manager management
pip install azure-mgmt-trafficmanager
```

### Verify Installation

```bash
az --version
python -c "from azure.identity import DefaultAzureCredential; from azure.mgmt.trafficmanager import TrafficManagerManagementClient; print('OK')"
```

## Credential Configuration

### Method A: Service Principal (Recommended for Automation)

**Create Service Principal**:
```bash
az ad sp create-for-rbac \
  --name "my-automation-sp" \
  --role "Traffic Manager Contributor" \
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
| Create Traffic Manager profile | Traffic Manager Contributor |
| Manage endpoints | Traffic Manager Contributor |
| Configure routing methods | Traffic Manager Contributor |

## Traffic Manager DNS Naming

Traffic Manager DNS names must be **globally unique**:
- Becomes: `{{dns-name}}.trafficmanager.net`
- Cannot conflict with any existing profile
- Use descriptive names with organization prefix

## Verify Credentials

```bash
az account show --output json
```

## Project-based Setup (pyproject.toml)

```toml
[project]
name = "azure-trafficmanager-ops"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "azure-identity>=1.10.0",
    "azure-mgmt-resource>=21.0.0",
    "azure-mgmt-trafficmanager>=1.0.0",
]
```

## Safety Rules

- **NEVER** commit `.env` files
- **NEVER** write credentials into Skill documents
- Generated Skills use `{{env.*}}` placeholders only
- Traffic Manager DNS names must be globally unique

## Full Command Reference (CLI + SDK Fallback)

Dual-path: Azure CLI is primary; on CLI failure retry up to 3×, then fall back to Azure SDK for Python.

### Create Profile

```bash
# Performance routing
az network traffic-manager profile create \
  --name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --routing-method Performance \
  --unique-dns-name "{{user.tm_dns_name}}" \
  --ttl 30 --protocol HTTPS --port 443 --path "/" --output json

# Priority routing (failover)
az network traffic-manager profile create \
  --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" \
  --routing-method Priority --unique-dns-name "{{user.tm_dns_name}}" \
  --ttl 30 --output json

# Weighted routing
az network traffic-manager profile create \
  --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" \
  --routing-method Weighted --unique-dns-name "{{user.tm_dns_name}}" \
  --ttl 30 --output json

# Geographic routing
az network traffic-manager profile create \
  --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" \
  --routing-method Geographic --unique-dns-name "{{user.tm_dns_name}}" \
  --ttl 30 --output json
```

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.trafficmanager import TrafficManagerManagementClient
import os

credential = DefaultAzureCredential()
client = TrafficManagerManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

profile = client.profiles.create_or_update(
    resource_group_name='{{user.resource_group}}',
    profile_name='{{user.tm_name}}',
    parameters={
        'location': 'global',
        'traffic_routing_method': 'Performance',
        'dns_config': {'relative_name': '{{user.tm_dns_name}}', 'ttl': 30},
        'monitor_config': {'protocol': 'HTTPS', 'port': 443, 'path': '/'}
    }
)
```

### Add Endpoint

```bash
# Azure endpoint
az network traffic-manager endpoint create \
  --name "endpoint-1" --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" --type azureEndpoints \
  --target-resource-id "{{user.target_resource_id}}" --endpoint-status enabled --output json

# External endpoint
az network traffic-manager endpoint create \
  --name "endpoint-external" --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" --type externalEndpoints \
  --target "{{user.external_fqdn}}" --endpoint-status enabled --output json

# Nested profile endpoint
az network traffic-manager endpoint create \
  --name "nested-profile" --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" --type nestedEndpoints \
  --target-resource-id "{{user.nested_profile_id}}" --endpoint-status enabled \
  --min-child-endpoints 2 --output json

# Priority routing
az network traffic-manager endpoint create \
  --name "endpoint-primary" --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" --type externalEndpoints \
  --target "{{user.primary_fqdn}}" --priority 1 --endpoint-status enabled --output json

# Weighted routing
az network traffic-manager endpoint create \
  --name "endpoint-weighted" --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" --type externalEndpoints \
  --target "{{user.target_fqdn}}" --weight 100 --endpoint-status enabled --output json

# Geographic routing
az network traffic-manager endpoint create \
  --name "endpoint-us" --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" --type externalEndpoints \
  --target "{{user.us_fqdn}}" --geo-mapping "US" --endpoint-status enabled --output json
```

### Update Endpoint Status

```bash
# Enable
az network traffic-manager endpoint update \
  --name "endpoint-1" --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" --endpoint-status enabled --output json

# Disable (maintenance)
az network traffic-manager endpoint update \
  --name "endpoint-1" --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" --endpoint-status disabled --output json
```

### Check Health

```bash
az network traffic-manager profile show \
  --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" --output json
# endpointMonitorStatus: Online / Degraded / Disabled / Inactive / CheckingEndpoint
```

### Delete Profile

```bash
az network traffic-manager profile show \
  --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" --output json
# confirm exact profile name, then:
az network traffic-manager profile delete \
  --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" --output json
```

### Recovery Table

| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| QuotaExceeded | HALT; request quota increase |
| NameNotAvailable | HALT; DNS name must be globally unique |
| Throttling (429) | Backoff, retry 3× |
| 5xx Internal | Retry 3×, then HALT |