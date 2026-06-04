---
name: azure-appgateway-ops
description: >-
  Use when operating Azure Application Gateway resources via Azure CLI or Azure SDK;
  user mentions "Application Gateway", "App Gateway", "AGW", "WAF", or L7 load balancing.
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

# Azure Application Gateway Operations Skill

## Overview

Azure Application Gateway provides **Layer 7 (L7)** application-level load balancing with SSL termination, URL-based routing, and Web Application Firewall (WAF). This skill is an operational runbook with explicit scope, credential rules, pre-flight checks, dual-path execution (Azure CLI + Azure SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "Application Gateway", "App Gateway", "AGW", "WAF"
- Task involves CRUD on **Application Gateway** resources
- Keywords: application gateway, backend pool, listener, rule, ssl certificate, waf, url routing
- L7 load balancing requirements (HTTP/HTTPS)
- SSL termination, URL path routing, cookie-based session affinity
- Web Application Firewall (WAF) protection

### SHOULD NOT Use When
- L4 (TCP/UDP) load balancing → delegate to: `azure-loadbalancer-ops`
- Global/multi-region load balancing → delegate to: `azure-frontdoor-ops`
- DNS-based routing → delegate to: `azure-trafficmanager-ops`
- Billing only → delegate to: `azure-cost-ops`
- VNet/Subnet only → delegate to: `azure-network-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.location}}` | User input | Azure region (e.g., eastus) |
| `{{user.agw_name}}` | User input | Application Gateway name; ask once |
| `{{output.agw_id}}` | Last API response | Parse: `.id` from Azure CLI output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create Application Gateway

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show` | HALT; configure env |
| Subscription valid | `az account list --output json` | Suggest valid subscription |
| Resource Group exists | `az group show --name {{user.resource_group}}` | Create or suggest existing |
| Location valid | `az account list-locations --output json` | Suggest valid location |
| VNet exists | `az network vnet show --name {{vnet}} --resource-group {{rg}}` | HALT; create VNet first |
| Subnet dedicated for AGW | Subnet must be dedicated, not shared | HALT; create dedicated subnet |
| Public IP exists | `az network public-ip show --name {{pip}} --resource-group {{rg}}` | HALT; create Public IP first |

#### Execute — Azure CLI (Primary)
```bash
# Create Application Gateway (basic setup)
az network application-gateway create \
  --name "{{user.agw_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --capacity 2 \
  --sku Standard_v2 \
  --public-ip-address "{{user.public_ip_name}}" \
  --vnet-name "{{user.vnet_name}}" \
  --subnet "{{user.subnet_name}}" \
  --servers "{{user.backend_server_addresses}}" \
  --output json

# Create with SSL certificate
az network application-gateway create \
  --name "{{user.agw_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --capacity 2 \
  --sku Standard_v2 \
  --public-ip-address "{{user.public_ip_name}}" \
  --vnet-name "{{user.vnet_name}}" \
  --subnet "{{user.subnet_name}}" \
  --servers "{{user.backend_server_addresses}}" \
  --cert-file "{{user.ssl_cert_path}}" \
  --cert-password "{{user.ssl_cert_password}}" \
  --output json

# Create with WAF enabled
az network application-gateway create \
  --name "{{user.agw_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --capacity 2 \
  --sku WAF_v2 \
  --public-ip-address "{{user.public_ip_name}}" \
  --vnet-name "{{user.vnet_name}}" \
  --subnet "{{user.subnet_name}}" \
  --servers "{{user.backend_server_addresses}}" \
  --output json
```

#### Execute — Azure SDK (Fallback)
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient
import os

credential = DefaultAzureCredential()
client = NetworkManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

# Create Application Gateway
agw = client.application_gateways.begin_create_or_update(
    resource_group_name='{{user.resource_group}}',
    application_gateway_name='{{user.agw_name}}',
    parameters={
        'location': '{{user.location}}',
        'sku': {
            'name': 'Standard_v2',
            'tier': 'Standard_v2',
            'capacity': 2
        },
        'gateway_ip_configurations': [{
            'name': 'gateway-ip-config',
            'subnet': {'id': '{{user.subnet_id}}'}
        }],
        'frontend_ip_configurations': [{
            'name': 'frontend-ip',
            'public_ip_address': {'id': '{{user.public_ip_id}}'}
        }],
        'frontend_ports': [{
            'name': 'port-80',
            'port': 80
        }],
        'backend_address_pools': [{
            'name': 'backend-pool',
            'backend_addresses': [{'fqdn': '{{user.backend_fqdn}}'}]
        }],
        'backend_http_settings': [{
            'name': 'http-settings',
            'port': 80,
            'protocol': 'Http'
        }],
        'http_listeners': [{
            'name': 'listener',
            'frontend_ip_configuration': {'id': 'frontend-ip-id'},
            'frontend_port': {'id': 'port-80-id'},
            'protocol': 'Http'
        }],
        'request_routing_rules': [{
            'name': 'rule',
            'rule_type': 'Basic',
            'http_listener': {'id': 'listener-id'},
            'backend_address_pool': {'id': 'backend-pool-id'},
            'backend_http_settings': {'id': 'http-settings-id'}
        }]
    }
).result()
```

#### Validate
```bash
# Verify Application Gateway state
az network application-gateway show --name "{{user.agw_name}}" --resource-group "{{user.resource_group}}" --output json

# Check operational state: should be "Running"
# Check provisioning state: should be "Succeeded"
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| QuotaExceeded | HALT; request quota increase |
| SubnetInUse | HALT; subnet must be dedicated for AGW |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |

### Operation: Add Backend Pool

```bash
# Create backend pool
az network application-gateway address-pool create \
  --gateway-name "{{user.agw_name}}" \
  --resource-group "{{user.resource_group}}" \
  --name "backend-pool-2" \
  --servers "{{user.backend_server_addresses}}" \
  --output json
```

### Operation: Configure URL Path Routing

```bash
# Create URL path map
az network application-gateway url-path-map create \
  --gateway-name "{{user.agw_name}}" \
  --resource-group "{{user.resource_group}}" \
  --name "url-path-map" \
  --path-rules "/images/*=backend-pool-images /api/*=backend-pool-api" \
  --default-address-pool "backend-pool-default" \
  --output json
```

### Operation: Enable WAF Policy

```bash
# Create WAF policy
az network application-gateway waf-policy create \
  --name "{{user.waf_policy_name}}" \
  --resource-group "{{user.resource_group}}" \
  --type OWASP \
  --version 3.0 \
  --output json

# Associate WAF policy with Application Gateway
az network application-gateway update \
  --name "{{user.agw_name}}" \
  --resource-group "{{user.resource_group}}" \
  --set wafConfiguration.enabled=true \
  --waf-policy "{{user.waf_policy_id}}" \
  --output json
```

### Operation: Delete Application Gateway

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

```bash
# Show Application Gateway before deletion
az network application-gateway show --name "{{user.agw_name}}" --resource-group "{{user.resource_group}}" --output json

# Request confirmation - user must type exact AGW name
# Then proceed with deletion:
az network application-gateway delete --name "{{user.agw_name}}" --resource-group "{{user.resource_group}}" --output json
```

## Application Gateway SKUs

| SKU | Tier | Use Case |
|-----|------|----------|
| **Standard_v2** | Standard | Auto-scaling, zone-redundant |
| **WAF_v2** | WAF | WAF protection + Standard_v2 features |
| **Basic** | Basic | Dev/test, limited features |

## Key Components

| Component | Purpose | CLI Command |
|-----------|---------|-------------|
| **Frontend IP** | Entry point | Auto-created with public IP |
| **Frontend Port** | Listen port | `az network application-gateway frontend-port create` |
| **Backend Pool** | Target servers | `az network application-gateway address-pool create` |
| **Backend HTTP Settings** | Backend config | `az network application-gateway http-settings create` |
| **HTTP Listener** | Protocol/port listener | `az network application-gateway http-listener create` |
| **Request Routing Rule** | Traffic routing | `az network application-gateway rule create` |
| **SSL Certificate** | SSL termination | `az network application-gateway ssl-cert create` |
| **URL Path Map** | URL-based routing | `az network application-gateway url-path-map create` |
| **WAF Policy** | Security policy | `az network application-gateway waf-policy create` |

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
- DELETE gateway (`az network application-gateway delete`) → **required**; traffic impact warning + Safety=0 → ABORT
- BACKEND POOL REMOVE (referenced by rule) → **required**; traffic disruption warning + Safety=0 → ABORT
- WAF POLICY enable/create → **required**; Detection vs Prevention mode confirmed
- SSL CERTIFICATE upload → **required**; password handled securely — NEVER in trace
- URL PATH MAP / LISTENER / RULE changes affecting active traffic → **required**; disruption warning
- CREATE gateway / LIST / SHOW → recommended

### SSL Certificate Password Security

SSL certificate passwords are sensitive credentials. The GCL trace MUST NOT contain
the `--cert-password` value. The Critic scans for password strings in command args
and output. If detected, safety=0 → ABORT, regardless of operation success.

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Application Gateway Docs](https://docs.microsoft.com/azure/application-gateway/)
- [Azure CLI App Gateway Reference](https://docs.microsoft.com/cli/azure/network/application-gateway)
- [WAF Configuration](https://docs.microsoft.com/azure/web-application-firewall/ag/ag-overview)