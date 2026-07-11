# Core Concepts — Azure DNS

## Purpose

Azure DNS provides domain name resolution (DNS) for Azure resources and external domains. Two zone types exist:
- **Public DNS Zones**: Resolvable from the internet; used for custom domain names on Azure services
- **Private DNS Zones**: Resolvable only within specified Azure Virtual Networks; used for internal name resolution

## Resource Hierarchy

| Resource | Azure provider type | Notes |
|----------|---------------------|-------|
| DNS Zone | `Microsoft.Network/dnsZones` (public) / `Microsoft.Network/privateDnsZones` | Requires Resource Group; global resource (no Location) |
| Record Set | `Microsoft.Network/dnsZones/<record-type>` | Child of DNS zone; relative name |
| Private DNS Zone VNet Link | `Microsoft.Network/privateDnsZones/virtualNetworkLinks` | Links private zone to a VNet |

Full DNS zone resource ID format:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Network/dnsZones/{{user.zone_name}}
```

Full record set resource ID format:

```text
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Network/dnsZones/{{user.zone_name}}/<record-type>/{{user.record_set_name}}
```

## Record Types

| Type | Value Format | Notes |
|------|-------------|-------|
| **A** | IPv4 address (e.g., `10.0.0.1`) | Maps domain to IPv4 |
| **AAAA** | IPv6 address (e.g., `2001:db8::1`) | Maps domain to IPv6 |
| **CNAME** | Canonical name (FQDN) | Alias to another domain; cannot coexist with other records at apex |
| **MX** | Priority + mail exchange host | Email routing |
| **NS** | Name server FQDN | Zone delegation; Azure auto-creates at zone apex |
| **SRV** | Priority + weight + port + target | Service discovery |
| **TXT** | Text string | Domain verification, SPF, DKIM, DMARC |
| **SOA** | Start of Authority (auto-managed) | Zone authority metadata; Azure manages automatically |
| **PTR** | Reverse FQDN | Reverse DNS lookup |
| **ALIAS** | Azure resource ID | Azure-specific; resolves to resource's public IP/FQDN automatically |

## Alias Records

Alias records are an Azure DNS feature that automatically resolves to an Azure resource's IP address or FQDN:
- Supports A, AAAA, CNAME record types
- Target types: Traffic Manager profiles, Front Door, CDN endpoints, Azure public IPs, App Service, other DNS zones
- Automatically updates when the target resource's IP changes
- Cannot point to external (non-Azure) resources

## TTL (Time-To-Live)

| Use Case | Recommended TTL | Notes |
|----------|----------------|-------|
| Production failover | 60-300 seconds | Faster failover, more DNS queries |
| Static resources | 3600-86400 seconds | Reduced query cost |
| Migration | 300-600 seconds | Balance between propagation speed and cost |
| Emergency change | 60 seconds | Fast propagation |

## Zone Delegation

To delegate a domain (e.g., `example.com`) to Azure DNS:
1. Create DNS zone with the domain name
2. Note the NS record values Azure assigns (4 name servers)
3. At your domain registrar, change NS records to Azure's name servers
4. Wait for DNS propagation (typically 24-48 hours)

## Operation Boundaries

This skill owns DNS zone, record set, zone import/export, private DNS zone VNet link, and DNS resolution troubleshooting workflows.

Delegate adjacent concerns:
- DNS-based global traffic routing → `azure-trafficmanager-ops`
- Global L7/CDN/SSL → `azure-frontdoor-ops`
- Application Gateway custom domain → `azure-appgateway-ops`
- VNet integration for private DNS → `azure-vnet-ops`
- Certificate validation → `azure-keyvault-ops`

## Safety Rules

- Deleting a DNS zone removes all records and breaks DNS delegation — all services using that domain will lose name resolution.
- Deleting a record set breaks DNS resolution for that name — confirm with user before deletion.
- CNAME records cannot coexist with other record types at the same name (RFC 1034).
- Private DNS zone deletion also removes all VNet links — services inside those VNets lose internal name resolution.
- Zone import can overwrite existing record sets — review the import file before execution.

## See Also

- [Azure DNS Documentation](https://docs.microsoft.com/azure/dns/)
- [Azure CLI DNS Reference](https://docs.microsoft.com/cli/azure/network/dns)
- [Azure SDK DNS Module](https://docs.microsoft.com/python/api/azure-mgmt-dns/)
- [Azure Private DNS Documentation](https://docs.microsoft.com/azure/dns/private-dns-overview)

## Validation Commands

```bash
az network dns zone show --name "{{user.zone_name}}" --resource-group "{{user.resource_group}}" --output json
az network dns record-set list --zone-name "{{user.zone_name}}" --resource-group "{{user.resource_group}}" --output json
az network dns record-set show --name "{{user.record_set_name}}" --zone-name "{{user.zone_name}}" --resource-group "{{user.resource_group}}" --record-type "{{user.record_type}}" --output json
az network private-dns zone show --name "{{user.zone_name}}" --resource-group "{{user.resource_group}}" --output json
```
