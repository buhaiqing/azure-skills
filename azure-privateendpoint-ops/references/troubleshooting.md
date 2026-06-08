# Azure Private Endpoint Troubleshooting

## Diagnostic Flow

1. Confirm subscription, Resource Group, and Private Endpoint name.
2. Show the Private Endpoint and inspect provisioning state.
3. Inspect the private service connection state.
4. Confirm subnet ID, private IP allocation, and network interface reference.
5. Inspect private DNS zone groups and DNS records.
6. Validate client DNS resolution and routing from inside the VNet.
7. Check Activity Log for recent `Microsoft.Network/privateEndpoints/*` and target-service Private Link connection events.
8. Escalate target service lifecycle issues to the target service skill.

## Common Errors

| Symptom / Error | Likely Cause | Action |
|-----------------|--------------|--------|
| `PrivateEndpointCannotBeCreatedInSubnetThatHasNetworkPoliciesEnabled` | Subnet policy conflicts | HALT; delegate subnet policy change to `azure-vnet-ops` |
| `InvalidPrivateLinkServiceId` | Target resource ID is not a valid Private Link target | Ask for full target resource ID |
| `GroupIdInvalid` | Wrong subresource group ID | Query supported group IDs or ask target service owner |
| Connection remains `Pending` | Manual approval required | Identify approver and do not assume connectivity works |
| DNS resolves public IP | Missing or wrong private DNS zone group | Validate zone IDs and records |
| Client cannot connect | NSG, route, DNS, or target firewall issue | Check DNS first, then NSG via `azure-nsg-ops` |
| `AuthorizationFailed` | Missing RBAC on network or target service | Require Network Contributor plus target-service approval rights |

## CLI Commands

```bash
az network private-endpoint show \
  --name {{user.private_endpoint_name}} \
  --resource-group {{user.resource_group}} \
  --output json

az network private-endpoint dns-zone-group list \
  --endpoint-name {{user.private_endpoint_name}} \
  --resource-group {{user.resource_group}} \
  --output json

az network private-endpoint-connection list \
  --id {{user.private_link_resource_id}} \
  --output json
```

## HALT vs Retry

| Condition | Decision |
|-----------|----------|
| Missing credentials | HALT |
| Missing Resource Group | HALT |
| Invalid subnet ID or target resource ID | HALT |
| Invalid group ID | HALT and ask for corrected input |
| Pending approval | HALT after reporting approver/action required |
| 429 throttling | Retry up to 3x with backoff |
| 5xx Azure error | Retry up to 3x, then HALT |
