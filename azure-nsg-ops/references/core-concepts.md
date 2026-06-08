# Azure Network Security Group Core Concepts

## Resource Model

A Network Security Group (NSG) is a Resource Group-scoped network security policy. It contains security rules and can be associated with:

- One or more subnets
- One or more network interfaces

Use full Azure resource IDs when crossing resource boundaries:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Network/networkSecurityGroups/{{user.nsg_name}}
```

## Security Rules

Each security rule evaluates traffic by:

| Field | Purpose |
|-------|---------|
| `priority` | Lower number wins; unique from 100 to 4096 per direction |
| `direction` | `Inbound` or `Outbound` |
| `access` | `Allow` or `Deny` |
| `protocol` | `Tcp`, `Udp`, `Icmp`, `Esp`, `Ah`, or `*` |
| `sourceAddressPrefix` | CIDR, service tag, application security group, or `*` |
| `sourcePortRange` | Port/range or `*` |
| `destinationAddressPrefix` | CIDR, service tag, application security group, or `*` |
| `destinationPortRange` | Port/range or `*` |

Default rules exist even when no custom rules are configured. Custom rules override defaults by priority.

## Association Behavior

Traffic is evaluated by both subnet-level and NIC-level NSGs when both exist. A deny in either effective policy blocks traffic. Before changing an association, inspect effective security rules for the target NIC when possible.

## Destructive and High-Risk Changes

Require explicit human confirmation before:

- Deleting an NSG
- Deleting a security rule
- Dissociating an NSG from a subnet or NIC
- Replacing a broad deny/allow rule that changes reachability

Always show the impacted subnet/NIC IDs and explain expected traffic exposure or outage.

## Delegation Boundaries

- Use `azure-vnet-ops` for address spaces, subnet creation, peering, and subnet delegation.
- Use `azure-privateendpoint-ops` for Private Endpoint lifecycle and Private Link approvals.
- Use `azure-vm-ops` for VM lifecycle and OS firewall troubleshooting.
