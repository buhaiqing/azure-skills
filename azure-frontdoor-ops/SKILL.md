---
name: azure-frontdoor-ops
description: >-
  Use when operating Azure Front Door resources via Azure CLI or Azure SDK;
  user mentions "Front Door", "FD", "Front Door Standard", "Front Door Premium", 
  or global/multi-region load balancing.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-05-10"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Front Door Operations Skill

## Overview

Azure Front Door provides **global Layer 7** load balancing with CDN acceleration, multi-region routing, and Web Application Firewall (WAF). This skill is an operational runbook with explicit scope, credential rules, pre-flight checks, dual-path execution (Azure CLI + Azure SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "Front Door", "FD", "Front Door Standard", "Front Door Premium"
- Task involves CRUD on **Front Door** resources
- Keywords: front door, frontend, backend pool, routing rule, health probe, origin group, endpoint, rule set
- Global/multi-region load balancing requirements
- CDN acceleration, caching, compression
- Web Application Firewall (WAF) at global edge

### SHOULD NOT Use When
- L4 (TCP/UDP) load balancing → delegate to: `azure-loadbalancer-ops`
- Single-region L7 load balancing → delegate to: `azure-appgateway-ops`
- DNS-based routing only → delegate to: `azure-trafficmanager-ops`
- Billing only → delegate to: `azure-cost-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.fd_name}}` | User input | Front Door profile name; ask once |
| `{{user.endpoint_name}}` | User input | Front Door endpoint name; ask once |
| `{{output.fd_id}}` | Last API response | Parse: `.id` from Azure CLI output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create Front Door Profile

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show` | HALT; configure env |
| Subscription valid | `az account list --output json` | Suggest valid subscription |
| Resource Group exists | `az group show --name {{user.resource_group}}` | Create or suggest existing |
| Front Door name globally unique | Front Door endpoint names must be globally unique | HALT; choose unique name |

#### Execute — Azure CLI (Primary)
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

#### Execute — Azure SDK (Fallback)
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.cdn import CdnManagementClient
import os

credential = DefaultAzureCredential()
client = CdnManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

# Create Front Door profile
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

#### Validate
```bash
# Verify Front Door profile state
az afd profile show --profile-name "{{user.fd_name}}" --resource-group "{{user.resource_group}}" --output json

# Verify endpoint state
az afd endpoint show --endpoint-name "{{user.endpoint_name}}" --profile-name "{{user.fd_name}}" --resource-group "{{user.resource_group}}" --output json

# Check provisioning state: should be "Succeeded"
# Check endpoint hostname: `{{endpoint_name}}-{{hash}}.azurefd.net`
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| QuotaExceeded | HALT; request quota increase |
| NameNotAvailable | HALT; endpoint name must be globally unique |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |

### Operation: Add Custom Domain

```bash
# Create custom domain
az afd custom-domain create \
  --custom-domain-name "{{user.custom_domain_name}}" \
  --profile-name "{{user.fd_name}}" \
  --resource-group "{{user.resource_group}}" \
  --host-name "{{user.custom_domain}}" \
  --certificate-type ManagedCertificate \
  --minimum-tls-version TLS12 \
  --output json

# Associate custom domain with endpoint
az afd route update \
  --route-name "route" \
  --endpoint-name "{{user.endpoint_name}}" \
  --profile-name "{{user.fd_name}}" \
  --resource-group "{{user.resource_group}}" \
  --custom-domains "{{user.custom_domain_name}}" \
  --output json
```

### Operation: Enable WAF Policy

```bash
# Create WAF policy
az network front-door waf-policy create \
  --name "{{user.waf_policy_name}}" \
  --resource-group "{{user.resource_group}}" \
  --mode Prevention \
  --output json

# Associate WAF policy with Front Door
az afd security-policy create \
  --security-policy-name "waf-policy" \
  --profile-name "{{user.fd_name}}" \
  --resource-group "{{user.resource_group}}" \
  --waf-policy "{{user.waf_policy_id}}" \
  --output json
```

### Operation: Delete Front Door Profile

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

```bash
# Show Front Door profile before deletion
az afd profile show --profile-name "{{user.fd_name}}" --resource-group "{{user.resource_group}}" --output json

# Request confirmation - user must type exact profile name
# Then proceed with deletion:
az afd profile delete --profile-name "{{user.fd_name}}" --resource-group "{{user.resource_group}}" --output json
```

## Front Door SKUs

| SKU | Use Case |
|-----|----------|
| **Standard_AzureFrontDoor** | Global load balancing, CDN acceleration |
| **Premium_AzureFrontDoor** | Standard + WAF, private link origins |

## Key Components

| Component | Purpose | CLI Command |
|-----------|---------|-------------|
| **Profile** | Front Door container | `az afd profile` |
| **Endpoint** | Entry point (hostname) | `az afd endpoint` |
| **Origin Group** | Backend pool | `az afd origin-group` |
| **Origin** | Backend server | `az afd origin` |
| **Health Probe** | Health check | `az afd probe` |
| **Route** | Routing rule | `az afd route` |
| **Custom Domain** | Custom hostname | `az afd custom-domain` |
| **Rule Set** | Traffic rules | `az afd rule-set` |
| **Security Policy** | WAF association | `az afd security-policy` |

## Front Door vs Application Gateway

| Feature | Front Door | Application Gateway |
|---------|------------|---------------------|
| Scope | Global/multi-region | Single-region |
| Layer | L7 (HTTP/HTTPS) | L7 (HTTP/HTTPS) |
| CDN | Built-in | Not available |
| WAF | Edge-level | Regional |
| SSL | Global certificate | Regional certificate |
| Routing | Global latency-based | URL-based |

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)

## See Also

- [Front Door Docs](https://docs.microsoft.com/azure/frontdoor/)
- [Azure CLI Front Door Reference](https://docs.microsoft.com/cli/azure/afd)
- [Front Door Standard vs Premium](https://docs.microsoft.com/azure/frontdoor/standard-premium/tier-comparison)