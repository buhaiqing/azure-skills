# Troubleshooting — Azure Virtual Network

## Error Decision Table

| Symptom / Error | Likely Cause | Action |
|-----------------|--------------|--------|
| `AddressPrefixOverlap` | Requested VNet/subnet CIDR overlaps existing range | HALT; ask for non-overlapping CIDR |
| `InvalidAddressPrefix` | CIDR syntax invalid or subnet outside VNet range | HALT; correct address prefix |
| `InUseSubnetCannotBeDeleted` | Subnet has NICs, private endpoints, gateways, or delegated resources | HALT; list dependencies, do not force delete |
| `SubnetIsFull` | Not enough available IPs | HALT; create larger subnet or add new subnet |
| `PeeringCannotBeCreatedOrUpdated` | Overlapping CIDR, missing permissions, or remote VNet issue | HALT; validate both VNets and RBAC |
| `AuthorizationFailed` | Missing Network Contributor or equivalent role | HALT; request RBAC fix |
| `ResourceNotFound` | Wrong Resource Group, VNet, or subnet name | Verify names and subscription |
| `AnotherOperationInProgress` | Network LRO still running | Wait and poll; do not start conflicting update |
| `TooManyRequests` / 429 | Azure throttling | Backoff and retry up to 3 times |
| 5xx | Azure control-plane transient issue | Retry up to 3 times, then HALT |

## Dependency Discovery Before Delete

Before subnet deletion, inspect common dependent resources:

```bash
az network vnet subnet show \
  --vnet-name "{{user.vnet_name}}" \
  --resource-group "{{user.resource_group}}" \
  --name "{{user.subnet_name}}" \
  --query "{id:id,ipConfigurations:ipConfigurations,privateEndpoints:privateEndpoints,delegations:delegations,routeTable:routeTable,networkSecurityGroup:networkSecurityGroup}" \
  --output json
```

Before VNet deletion:

```bash
az network vnet show \
  --name "{{user.vnet_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "{id:id,subnets:subnets[].{name:name,id:id,ipConfigurations:ipConfigurations,privateEndpoints:privateEndpoints},peerings:virtualNetworkPeerings}" \
  --output json
```

## Address Overlap Checks

List existing VNets in the subscription:

```bash
az network vnet list \
  --query "[].{resourceGroup:resourceGroup,name:name,location:location,addressSpace:addressSpace.addressPrefixes}" \
  --output json
```

For peering requests, compare both VNet address spaces and HALT if any CIDR overlaps.

## Polling Strategy

Network create/update/delete operations are Azure long-running operations. Poll every 15 seconds for up to 20 minutes:

```bash
az network vnet show \
  --name "{{user.vnet_name}}" \
  --resource-group "{{user.resource_group}}" \
  --query "provisioningState" \
  --output tsv
```

Expected terminal state: `Succeeded`. If provisioning stays `Updating` beyond the max wait, HALT and inspect Activity Log.

## Activity Log

```bash
az monitor activity-log list \
  --resource-group "{{user.resource_group}}" \
  --status Failed \
  --max-events 20 \
  --output json
```

Use Activity Log to identify policy denial, RBAC denial, quota, and platform failures.

## Safety Handling

- Never bypass confirmation for subnet/VNet deletion.
- Never delete a subnet with dependent resources still attached.
- Never shrink address space without proving all existing subnets still fit.
- Never print `{{env.AZURE_CLIENT_SECRET}}` or credential values in traces.
