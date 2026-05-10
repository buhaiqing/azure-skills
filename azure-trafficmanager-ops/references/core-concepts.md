# Azure Traffic Manager Core Concepts

## What is Azure Traffic Manager

- **Purpose**: DNS-based global traffic routing and load balancing
- **Category**: Network / DNS Load Balancing
- **Portal**: https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.Network%2FtrafficManagerProfiles
- **Docs**: https://docs.microsoft.com/azure/traffic-manager/
- **Pricing**: https://azure.microsoft.com/pricing/details/traffic-manager/

## Primary Resources

| Resource | Description | Portal Path |
|----------|-------------|-------------|
| Traffic Manager Profile | DNS routing profile | /Microsoft.Network/trafficManagerProfiles |
| Endpoint | Target endpoint (Azure/External/Nested) | Endpoint |
| DNS Configuration | DNS name and TTL | DNS configuration |
| Monitor Configuration | Health check settings | Monitor configuration |

## Architecture & Limits

### Resource ID Format
```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Network/trafficmanagerprofiles/{profile-name}
```

### DNS Name Format
```
{dns-name}.trafficmanager.net
```

### Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| Traffic Manager profiles per subscription | 1000 | Yes |
| Endpoints per profile | 200 | Yes |
| Nested profiles depth | 10 levels | No |

### Routing Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| **Performance** | Route to lowest latency endpoint | Global performance optimization |
| **Priority** | Route to primary, failover to backup | Active-passive failover |
| **Weighted** | Distribute traffic by weight | Load distribution, gradual rollout |
| **Geographic** | Route based on user geography | Regional compliance, localization |
| **Subnet** | Route based on IP subnet | Specific network routing |
| **MultiValue** | Return multiple endpoints | Client-side load balancing |

## Routing Method Details

### Performance Routing
- Measures latency to each endpoint
- Routes to endpoint with lowest latency
- Based on user's DNS query location
- Best for: Global performance optimization

### Priority Routing
- Primary endpoint receives all traffic
- Failover to secondary if primary fails
- Multiple failover levels (primary → secondary → tertiary)
- Best for: Active-passive disaster recovery

### Weighted Routing
- Distribute traffic based on weight values
- Weight 100 = normal, weight 200 = double traffic
- Useful for gradual rollouts (10% → 50% → 100%)
- Best for: Load distribution, A/B testing

### Geographic Routing
- Routes based on user's geographic location
- Maps regions to specific endpoints
- Supports country/region-level mapping
- Best for: Regional compliance, localization

### Subnet Routing
- Routes based on user's IP subnet
- Maps IP ranges to specific endpoints
- Useful for internal/VPN traffic routing
- Best for: Specific network routing

### MultiValue Routing
- Returns multiple healthy endpoints in DNS response
- Client chooses which endpoint to use
- Typically returns 2-8 endpoints
- Best for: Client-side load balancing

## Endpoint Types

| Type | Target | Description |
|------|--------|-------------|
| **azureEndpoints** | Azure resource ID | Web App, Public IP, etc. |
| **externalEndpoints** | FQDN or IP | Non-Azure endpoints |
| **nestedEndpoints** | Profile ID | Nested Traffic Manager profile |

## Endpoint Health Monitoring

### Monitor Configuration
| Setting | Description | Default |
|---------|-------------|---------|
| Protocol | HTTP, HTTPS, TCP | HTTP |
| Port | Port number | 80 (HTTP), 443 (HTTPS) |
| Path | URL path for health check | "/" |
| Interval | Check interval in seconds | 30 |
| Timeout | Timeout in seconds | 10 |
| Tolerated failures | Failures before marking degraded | 3 |

### Endpoint Status Values
| Status | Meaning |
|--------|---------|
| **Online** | Healthy, receiving traffic |
| **Degraded** | Health check failing, may receive traffic |
| **Disabled** | Manually disabled |
| **Inactive** | Profile disabled or below min endpoints |
| **CheckingEndpoint** | Initial health check |

## Resource Lifecycle

| Profile Status | Description | Allowed Operations |
|----------------|-------------|-------------------|
| Enabled | Active routing | All operations |
| Disabled | No routing | Enable, modify |

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| Resource Group | Yes | `azure-resource-ops` |
| Target endpoints | Yes | External or Azure resources |

## Best Practices

### High Availability
- Configure at least 2 endpoints per profile
- Use appropriate routing method for your use case
- Configure proper health check settings
- Monitor endpoint health status

### Failover Design
- Use Priority routing for DR
- Set primary in one region, secondary in another
- Configure proper health check sensitivity
- Test failover periodically

### Performance Optimization
- Use Performance routing for global apps
- Deploy endpoints in multiple regions
- Monitor latency metrics
- Adjust TTL appropriately

### Geographic Routing
- Use Geographic routing for compliance
- Map countries/regions to appropriate endpoints
- Consider edge cases (unknown regions)
- Test with different geographic locations

## Pricing Model

- **Pricing type**: Per profile + DNS queries + health checks
- **Key dimensions**: Profiles, DNS queries, endpoint health checks
- **Free tier**: None
- **Estimator**: https://azure.microsoft.com/pricing/calculator/

## Traffic Manager vs Front Door

| Feature | Traffic Manager | Front Door |
|---------|-----------------|------------|
| Layer | DNS (no proxy) | L7 proxy |
| Routing method | Multiple | Latency-based |
| CDN | No | Yes |
| WAF | No | Yes (Premium) |
| Health check | Active | Active |
| Response time | DNS only | Full proxy |
| SSL | At endpoint | At edge |

## Common Patterns

### Pattern 1: Global Failover
- Use case: Multi-region disaster recovery
- Architecture: TM → Primary region + Secondary region
- Steps:
  1. Create Traffic Manager profile with Priority routing
  2. Add primary endpoint (priority 1)
  3. Add secondary endpoint (priority 2)
  4. Configure health check
  5. Traffic fails over automatically when primary fails

### Pattern 2: Geographic Routing
- Use case: Regional data compliance
- Architecture: TM → Endpoints per region
- Steps:
  1. Create Traffic Manager profile with Geographic routing
  2. Add endpoints with geographic mapping
  3. Map regions to endpoints (US → endpoint1, EU → endpoint2)
  4. Configure health check per endpoint

### Pattern 3: Gradual Rollout
- Use case: New version deployment
- Architecture: TM → Old version + New version (weighted)
- Steps:
  1. Create Traffic Manager profile with Weighted routing
  2. Add old version endpoint (weight 90)
  3. Add new version endpoint (weight 10)
  4. Gradually increase new version weight
  5. Remove old version after 100% rollout

### Pattern 4: Hybrid Cloud
- Use case: Azure + On-premises
- Architecture: TM → Azure endpoint + External endpoint
- Steps:
  1. Create Traffic Manager profile
  2. Add Azure endpoint (type: azureEndpoints)
  3. Add on-premises endpoint (type: externalEndpoints)
  4. Configure routing method (Priority or Weighted)