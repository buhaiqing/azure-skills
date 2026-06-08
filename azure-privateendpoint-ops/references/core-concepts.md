# Azure Private Endpoint Core Concepts

## Resource Model

A Private Endpoint is a network interface with a private IP address in a subnet. It connects privately to a target Azure resource through Private Link.

Full resource ID form is required for subnet, target service, Private Endpoint, and private DNS zone references:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Network/privateEndpoints/{{user.private_endpoint_name}}
```

## Required Inputs

| Input | Purpose |
|-------|---------|
| Resource Group | Owns the Private Endpoint resource |
| Location | Azure Location for the Private Endpoint |
| Subnet ID | Full subnet resource ID where the private IP is allocated |
| Private Link resource ID | Full target service resource ID |
| Group ID | Target subresource, such as `blob`, `file`, `vault`, or `sites` |
| Connection name | Name for the private service connection |
| Private DNS zone ID | Optional full private DNS zone resource ID for name resolution |

## Connection States

Private Endpoint connections can be:

- `Approved`: traffic can use the private endpoint.
- `Pending`: target service owner must approve.
- `Rejected`: connection is not usable.
- `Disconnected`: target service removed or connection broken.

Do not treat `Succeeded` provisioning as equivalent to usable connectivity. Validate both provisioning state and connection state.

## DNS Integration

Private DNS zone groups link the Private Endpoint to one or more private DNS zones. Incorrect DNS integration often causes clients to resolve the public endpoint instead of the private IP.

Before deleting or changing DNS zone groups, show the zone IDs and expected name resolution impact.

## Destructive and High-Risk Changes

Require explicit human confirmation before:

- Deleting a Private Endpoint
- Deleting a private DNS zone group
- Rejecting a Private Link connection
- Removing DNS integration

Always show target resource ID, subnet ID, private IP, connection state, and DNS zone IDs.

## Delegation Boundaries

- Use `azure-vnet-ops` for subnet creation, address space, peering, and subnet policy changes.
- Use `azure-nsg-ops` for NSG and security rule changes.
- Use the target service skill for storage account, Key Vault, App Service, AKS, VM, or other service lifecycle.
