---
name: azure-trafficmanager-ops
description: >-
  Use when operating Azure Traffic Manager resources via Azure CLI or Azure SDK;
  user mentions "Traffic Manager", "TM", "DNS load balancing", or "global routing".
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints.
metadata:
  author: azure
  version: "1.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Traffic Manager Operations Skill

## Overview

Azure Traffic Manager provides **DNS-based** global load balancing for routing traffic across multiple regions and endpoints. This skill is an operational runbook with explicit scope, credential rules, pre-flight checks, dual-path execution (Azure CLI + Azure SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "Traffic Manager", "TM", "DNS load balancing", "global routing"
- Task involves CRUD on **Traffic Manager** resources
- Keywords: traffic manager, profile, endpoint, routing method, priority, weight, geographic, performance
- DNS-based traffic routing
- Global/multi-region failover
- Performance-based routing (latency)

### SHOULD NOT Use When
- L4/L7 load balancing with proxy → delegate to: `azure-loadbalancer-ops` or `azure-appgateway-ops`
- CDN acceleration → delegate to: `azure-frontdoor-ops`
- Billing only → delegate to: `azure-cost-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.tm_name}}` | User input | Traffic Manager profile name; ask once |
| `{{output.tm_id}}` | Last API response | Parse: `.id` from Azure CLI output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create Traffic Manager Profile

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show` | HALT; configure env |
| Subscription valid | `az account list --output json` | Suggest valid subscription |
| Resource Group exists | `az group show --name {{user.resource_group}}` | Create or suggest existing |
| Profile name globally unique | DNS name must be unique | HALT; choose unique name |

#### Execute — Azure CLI (Primary)
```bash
# Create Traffic Manager profile (Performance routing)
az network traffic-manager profile create \
  --name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --routing-method Performance \
  --unique-dns-name "{{user.tm_dns_name}}" \
  --ttl 30 \
  --protocol HTTPS \
  --port 443 \
  --path "/" \
  --output json

# Create Traffic Manager profile (Priority routing - failover)
az network traffic-manager profile create \
  --name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --routing-method Priority \
  --unique-dns-name "{{user.tm_dns_name}}" \
  --ttl 30 \
  --output json

# Create Traffic Manager profile (Weighted routing)
az network traffic-manager profile create \
  --name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --routing-method Weighted \
  --unique-dns-name "{{user.tm_dns_name}}" \
  --ttl 30 \
  --output json

# Create Traffic Manager profile (Geographic routing)
az network traffic-manager profile create \
  --name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --routing-method Geographic \
  --unique-dns-name "{{user.tm_dns_name}}" \
  --ttl 30 \
  --output json
```

#### Execute — Azure SDK (Fallback)
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.trafficmanager import TrafficManagerManagementClient
import os

credential = DefaultAzureCredential()
client = TrafficManagerManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

# Create Traffic Manager profile
profile = client.profiles.create_or_update(
    resource_group_name='{{user.resource_group}}',
    profile_name='{{user.tm_name}}',
    parameters={
        'location': 'global',
        'traffic_routing_method': 'Performance',
        'dns_config': {
            'relative_name': '{{user.tm_dns_name}}',
            'ttl': 30
        },
        'monitor_config': {
            'protocol': 'HTTPS',
            'port': 443,
            'path': '/'
        }
    }
)
```

#### Validate
```bash
# Verify Traffic Manager profile state
az network traffic-manager profile show --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" --output json

# Check provisioning state: should be "Succeeded"
# Check DNS name: `{{tm_dns_name}}.trafficmanager.net`
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| QuotaExceeded | HALT; request quota increase |
| NameNotAvailable | HALT; DNS name must be globally unique |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |

### Operation: Add Endpoint

```bash
# Add Azure endpoint (Web App, VM, etc.)
az network traffic-manager endpoint create \
  --name "endpoint-1" \
  --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --type azureEndpoints \
  --target-resource-id "{{user.target_resource_id}}" \
  --endpoint-status enabled \
  --output json

# Add external endpoint (non-Azure)
az network traffic-manager endpoint create \
  --name "endpoint-external" \
  --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --type externalEndpoints \
  --target "{{user.external_fqdn}}" \
  --endpoint-status enabled \
  --output json

# Add nested profile endpoint
az network traffic-manager endpoint create \
  --name "nested-profile" \
  --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --type nestedEndpoints \
  --target-resource-id "{{user.nested_profile_id}}" \
  --endpoint-status enabled \
  --min-child-endpoints 2 \
  --output json

# Add endpoint with priority (for Priority routing)
az network traffic-manager endpoint create \
  --name "endpoint-primary" \
  --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --type externalEndpoints \
  --target "{{user.primary_fqdn}}" \
  --priority 1 \
  --endpoint-status enabled \
  --output json

# Add endpoint with weight (for Weighted routing)
az network traffic-manager endpoint create \
  --name "endpoint-weighted" \
  --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --type externalEndpoints \
  --target "{{user.target_fqdn}}" \
  --weight 100 \
  --endpoint-status enabled \
  --output json

# Add endpoint with geographic mapping (for Geographic routing)
az network traffic-manager endpoint create \
  --name "endpoint-us" \
  --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --type externalEndpoints \
  --target "{{user.us_fqdn}}" \
  --geo-mapping "US" \
  --endpoint-status enabled \
  --output json
```

### Operation: Update Endpoint Status

```bash
# Enable endpoint
az network traffic-manager endpoint update \
  --name "endpoint-1" \
  --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --endpoint-status enabled \
  --output json

# Disable endpoint (for maintenance)
az network traffic-manager endpoint update \
  --name "endpoint-1" \
  --profile-name "{{user.tm_name}}" \
  --resource-group "{{user.resource_group}}" \
  --endpoint-status disabled \
  --output json
```

### Operation: Check Endpoint Health

```bash
# Get Traffic Manager profile health
az network traffic-manager profile show --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" --output json

# Check endpoint status in profile response
# Endpoints have "endpointMonitorStatus": "Online" / "Degraded" / "Disabled" / "Inactive"
```

### Operation: Delete Traffic Manager Profile

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

```bash
# Show Traffic Manager profile before deletion
az network traffic-manager profile show --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" --output json

# Request confirmation - user must type exact profile name
# Then proceed with deletion:
az network traffic-manager profile delete --name "{{user.tm_name}}" --resource-group "{{user.resource_group}}" --output json
```

## Routing Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| **Performance** | Route to lowest latency endpoint | Global performance optimization |
| **Priority** | Route to primary, failover to backup | Active-passive failover |
| **Weighted** | Distribute traffic by weight | Load distribution, gradual rollout |
| **Geographic** | Route based on user geography | Regional compliance, localization |
| **Subnet** | Route based on IP subnet | Specific network routing |
| **MultiValue** | Return multiple endpoints | Client-side load balancing |

## Endpoint Types

| Type | Description | Target |
|------|-------------|--------|
| **azureEndpoints** | Azure resource | Resource ID (Web App, VM, etc.) |
| **externalEndpoints** | Non-Azure endpoint | FQDN or IP address |
| **nestedEndpoints** | Nested Traffic Manager profile | Profile ID |

## Endpoint Monitor Status

| Status | Meaning |
|--------|---------|
| **Online** | Healthy, receiving traffic |
| **Degraded** | Health check failing, may receive traffic |
| **Disabled** | Manually disabled |
| **Inactive** | Profile disabled or below min endpoints |
| **CheckingEndpoint** | Initial health check in progress |

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate.
See `AGENTS.md §3–§8` for the spec.

| Parameter | Value |
|-----------|-------|
| GCL | **required** |
| max_iterations | 2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE profile (`az network traffic-manager profile delete`) → **required**; DNS impact warning + Safety=0 → ABORT
- DELETE endpoint → **required**; traffic reroute to remaining endpoints communicated
- DISABLE endpoint (last healthy) → **required**; check if any other endpoint is Online; degradation warning + Safety=0 → ABORT
- CHANGE routing method → **required**; traffic redistribution impact communicated
- CREATE profile / ADD endpoint / ENABLE endpoint / UPDATE → recommended

### Note on DNS Propagation

Traffic Manager is DNS-based — changes propagate gradually based on `--ttl` (default 30s, but client DNS caches may be longer).
The GCL trace should note TTL value and propagation characteristics.

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Traffic Manager Docs](https://docs.microsoft.com/azure/traffic-manager/)
- [Azure CLI Traffic Manager Reference](https://docs.microsoft.com/cli/azure/network/traffic-manager)
- [Routing Methods](https://docs.microsoft.com/azure/traffic-manager/traffic-manager-routing-methods)
