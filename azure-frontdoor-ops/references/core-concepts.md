# Azure Front Door Core Concepts

## What is Azure Front Door

- **Purpose**: Global Layer 7 load balancing with CDN acceleration and WAF at edge
- **Category**: Network / Global Application Delivery
- **Portal**: https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.Cdn%2Fprofiles
- **Docs**: https://docs.microsoft.com/azure/frontdoor/
- **Pricing**: https://azure.microsoft.com/pricing/details/frontdoor/

## Primary Resources

| Resource | Description | Portal Path |
|----------|-------------|-------------|
| Front Door Profile | Container for Front Door resources | /Microsoft.Cdn/profiles |
| Endpoint | Entry point with unique hostname | Front Door endpoint |
| Origin Group | Backend pool with health probe | Origin group |
| Origin | Backend server (IP/FQDN) | Origin |
| Route | Routing rule mapping endpoint to origin | Route |
| Custom Domain | Custom hostname | Custom domain |
| Rule Set | Traffic manipulation rules | Rule set |
| Security Policy | WAF association | Security policy |
| Health Probe | Origin health check | Health probe |

## Architecture & Limits

### Resource ID Format
```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Cdn/profiles/{profile-name}
```

### SKU Comparison

| Feature | Standard | Premium |
|---------|----------|---------|
| Global load balancing | Yes | Yes |
| CDN acceleration | Yes | Yes |
| WAF | No | Yes |
| Private Link origins | No | Yes |
| Bot protection | No | Yes |
| Max origins per group | 50 | 50 |
| Max endpoints | 100 | 100 |

### Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| Front Door profiles per subscription | 100 | Yes |
| Endpoints per profile | 100 | Yes |
| Origin groups per profile | 100 | Yes |
| Origins per group | 50 | Yes |
| Routes per endpoint | 100 | Yes |
| Custom domains per profile | 500 | Yes |

### Global Edge Locations
- 200+ edge locations worldwide
- Automatic routing to nearest edge
- Anycast IP for global reachability

## Features

### Global Load Balancing
- Latency-based routing to nearest healthy origin
- Automatic failover to secondary origin
- Multi-region deployment support

### CDN Acceleration
- Content caching at edge
- Compression (gzip, brotli)
- Cache rules per route
- Query string caching behavior

### SSL/TLS
- Managed SSL certificates (free)
- Custom SSL certificates
- HTTPS-only enforcement
- TLS 1.2 minimum

### Web Application Firewall (Premium)
- OWASP CRS 3.2
- Custom rules
- Bot protection
- Rate limiting
- Geographic filtering

### Traffic Rules
- URL rewrite
- Header manipulation
- Query string manipulation
- Redirect rules
- Cache rules

## Resource Lifecycle

| Provisioning State | Description | Allowed Operations |
|--------------------|-------------|-------------------|
| Succeeded | Operational | All operations |
| Creating | Initial provisioning | Wait |
| Deleting | Deletion in progress | Wait |
| Failed | Terminal error state | Delete |

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| Resource Group | Yes | `azure-resource-ops` |
| Origin (backend) | Yes | External or Azure resource |
| WAF Policy (for Premium) | Optional | `azure-waf-ops` |

## Best Practices

### High Availability
- Deploy origins in multiple regions
- Configure health probes for each origin
- Set appropriate failover priority
- Use at least 2 origins per group

### Performance
- Enable caching for static content
- Configure compression
- Use appropriate cache rules
- Optimize origin response time

### Security
- Use Premium SKU with WAF for production
- Enable HTTPS-only
- Configure WAF in Prevention mode
- Use managed SSL certificates
- Enable geographic filtering if needed

## Pricing Model

- **Pricing type**: Data transfer + requests + origin traffic
- **Key dimensions**: Data transfer, requests, origin fetch
- **Free tier**: None
- **Estimator**: https://azure.microsoft.com/pricing/calculator/

## Front Door vs Application Gateway

| Feature | Front Door | Application Gateway |
|---------|------------|---------------------|
| Scope | Global | Regional |
| Layer | L7 | L7 |
| CDN | Yes | No |
| Edge locations | 200+ | Single region |
| WAF | Edge-level | Regional |
| SSL | Global managed | Regional |
| Private Link origins | Premium only | Supported |

## Common Patterns

### Pattern 1: Global Web Application
- Use case: Multi-region web application
- Architecture: FD → Origins in multiple regions
- Steps:
  1. Create Front Door profile (Standard)
  2. Create endpoint
  3. Create origin group with origins in multiple regions
  4. Configure health probe
  5. Create route

### Pattern 2: API Gateway with WAF
- Use case: Secure global API
- Architecture: FD Premium → WAF → API origins
- Steps:
  1. Create Front Door profile (Premium)
  2. Create WAF policy with OWASP CRS
  3. Associate security policy
  4. Configure origins and routes
  5. Add rate limiting rules

### Pattern 3: Static Content CDN
- Use case: Static assets caching
- Architecture: FD → Origin (storage/app)
- Steps:
  1. Create Front Door profile
  2. Create route with cache rules
  3. Enable compression
  4. Configure cache TTL
  5. Use query string caching

### Pattern 4: Failover Architecture
- Use case: Regional disaster recovery
- Architecture: FD → Primary region + Secondary region
- Steps:
  1. Create origins for primary and secondary regions
  2. Configure health probes
  3. Set priority: primary first, secondary backup
  4. FD automatically routes to healthy origin

## Key Components (CLI Command Family)

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

## Front Door SKUs

| SKU | Use Case |
|-----|----------|
| **Standard_AzureFrontDoor** | Global load balancing, CDN acceleration |
| **Premium_AzureFrontDoor** | Standard + WAF, private link origins |