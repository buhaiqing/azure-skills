# Core Concepts — Azure Virtual Network

## Purpose

Azure Virtual Network (VNet) is the private networking boundary for Azure workloads. A VNet contains address spaces and subnets, and other resources attach through NICs, private endpoints, delegated subnets, or service integrations.

## Resource Hierarchy

| Resource | Azure provider type | Notes |
|----------|---------------------|-------|
| Virtual Network | `Microsoft.Network/virtualNetworks` | Requires Resource Group and Location |
| Subnet | `Microsoft.Network/virtualNetworks/subnets` | Child resource; no separate Location |
| VNet Peering | `Microsoft.Network/virtualNetworks/virtualNetworkPeerings` | Links two VNets; configure both directions |

Full VNet resource ID format:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Network/virtualNetworks/{{user.vnet_name}}
```

Full subnet resource ID format:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Network/virtualNetworks/{{user.vnet_name}}/subnets/{{user.subnet_name}}
```

## Address Planning

| Concept | Guidance |
|---------|----------|
| Address space | Use private RFC1918 CIDR ranges; avoid overlap across peered/on-prem networks |
| Subnet prefix | Must be contained inside VNet address space |
| Reserved IPs | Azure reserves 5 IPs per subnet |
| Peering | Overlapping address spaces cannot be peered |
| App Gateway subnet | Dedicated subnet, commonly `/26` or larger |
| AKS subnet | Size for node count, pods, and upgrade surge |

## Common Subnet Types

| Subnet type | Typical use | Notes |
|-------------|-------------|-------|
| `app-subnet` | VM, App Service VNet integration, app tiers | Attach NSG/route table as needed |
| `GatewaySubnet` | VPN/ExpressRoute gateway | Name must be exactly `GatewaySubnet` |
| `AzureFirewallSubnet` | Azure Firewall | Name must be exactly `AzureFirewallSubnet` |
| `agw-subnet` | Application Gateway | Dedicated; do not mix with other resources |
| delegated subnet | PaaS delegation | Use `az network vnet subnet update --delegations` |

## Operation Boundaries

This skill owns VNet, subnet, peering, address prefix, service endpoint, DNS server, and subnet delegation workflows.

Delegate adjacent concerns:
- NSG rule authoring → future `azure-nsg-ops`
- Load Balancer → `azure-loadbalancer-ops`
- Application Gateway → `azure-appgateway-ops`
- VM NIC attachment → `azure-vm-ops`
- Private DNS zone records → future DNS-specific skill

## Safety Rules

- Deleting a subnet can break NICs, private endpoints, gateways, App Gateway, AKS, and delegated services.
- Deleting a VNet deletes its subnets and breaks all attached network paths.
- Address space shrink/update can invalidate existing subnets or peering.
- Peering changes can break cross-VNet service connectivity.

For destructive or connectivity-impacting operations, show dependencies and obtain exact-name human confirmation before execution.

## Validation Commands

```bash
az network vnet show --name "{{user.vnet_name}}" --resource-group "{{user.resource_group}}" --output json
az network vnet subnet list --vnet-name "{{user.vnet_name}}" --resource-group "{{user.resource_group}}" --output json
az network vnet peering list --vnet-name "{{user.vnet_name}}" --resource-group "{{user.resource_group}}" --output json
```
