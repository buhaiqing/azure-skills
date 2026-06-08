# Azure Network Security Group Troubleshooting

## Diagnostic Flow

1. Confirm subscription and Resource Group.
2. Show the NSG and security rules.
3. Check subnet and NIC associations.
4. For VM traffic, inspect effective security rules on the NIC.
5. Compare requested flow against custom and default rules.
6. Check Activity Log for recent `Microsoft.Network/networkSecurityGroups/*` write/delete events.
7. Validate route tables, Azure Firewall, load balancer probes, and guest OS firewall only after NSG rules are ruled out.

## Common Errors

| Symptom / Error | Likely Cause | Action |
|-----------------|--------------|--------|
| `SecurityRuleConflict` | Duplicate priority in same direction | Choose an unused priority from 100 to 4096 |
| `InvalidSecurityRulePriority` | Priority outside valid range | Use 100-4096 |
| `InvalidAddressPrefix` | CIDR, service tag, or wildcard invalid | Correct source/destination prefix |
| `InvalidPortRange` | Port or range invalid | Use `*`, single port, or valid range |
| `InUseNetworkSecurityGroupCannotBeDeleted` | NSG still associated | HALT; show associations and request confirmation before dissociation |
| `AuthorizationFailed` | Missing RBAC | Require Network Contributor or equivalent |
| Traffic unexpectedly blocked | Deny rule or default deny wins | Inspect effective rules and matching priority |
| Traffic unexpectedly allowed | Broad allow or missing deny | Identify matching allow and propose narrower rule |

## CLI Commands

```bash
az network nsg show \
  --name {{user.nsg_name}} \
  --resource-group {{user.resource_group}} \
  --output json

az network nsg rule list \
  --nsg-name {{user.nsg_name}} \
  --resource-group {{user.resource_group}} \
  --output json

az network nic list-effective-nsg \
  --name {{user.nic_name}} \
  --resource-group {{user.resource_group}} \
  --output json
```

## HALT vs Retry

| Condition | Decision |
|-----------|----------|
| Missing credentials | HALT |
| Missing Resource Group | HALT |
| Invalid rule priority/prefix/port | HALT and ask for corrected input |
| NSG in use during delete | HALT; require confirmation and dependency plan |
| 429 throttling | Retry up to 3x with backoff |
| 5xx Azure error | Retry up to 3x, then HALT |
