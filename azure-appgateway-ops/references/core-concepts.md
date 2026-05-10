# Azure Application Gateway Core Concepts

## What is Azure Application Gateway

- **Purpose**: Layer 7 (L7) application-level load balancing with SSL termination, URL routing, and WAF
- **Category**: Network / Application Delivery Controller
- **Portal**: https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.Network%2FapplicationGateways
- **Docs**: https://docs.microsoft.com/azure/application-gateway/
- **Pricing**: https://azure.microsoft.com/pricing/details/application-gateway/

## Primary Resources

| Resource | Description | Portal Path |
|----------|-------------|-------------|
| Application Gateway | L7 load balancer resource | /Microsoft.Network/applicationGateways |
| Backend Pool | Target servers (IP/FQDN) | Backend address pool |
| Frontend IP | Entry point (public/internal) | Frontend IP configuration |
| Frontend Port | Listener port | Frontend port |
| HTTP Listener | Protocol/port listener | HTTP listener |
| Backend HTTP Settings | Backend connection settings | Backend HTTP settings |
| Request Routing Rule | Traffic routing logic | Request routing rule |
| SSL Certificate | SSL termination certificate | SSL certificate |
| WAF Policy | Web Application Firewall policy | WAF policy |
| URL Path Map | URL-based routing rules | URL path map |

## Architecture & Limits

### Resource ID Format
```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Network/applicationGateways/{agw-name}
```

### SKU Comparison

| Feature | Standard_v2 | WAF_v2 | Basic |
|---------|-------------|--------|-------|
| Auto-scaling | Yes | Yes | Fixed |
| Zone redundancy | Yes | Yes | No |
| WAF | No | Yes | No |
| Max instances | 125 | 125 | Fixed |
| SSL termination | Yes | Yes | Yes |
| URL routing | Yes | Yes | Limited |

### Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| Application Gateways per subscription | 1000 | Yes |
| Backend pools per gateway | 100 | Yes |
| HTTP listeners per gateway | 100 | Yes |
| Rules per gateway | 100 | Yes |
| SSL certificates per gateway | 100 | Yes |

### Subnet Requirements
- Dedicated subnet (not shared with other resources)
- Minimum 32 IP addresses in subnet
- Subnet must be in same VNet as Application Gateway

## Features

### SSL Termination
- Offload SSL decryption at gateway
- Backend traffic can be HTTP or HTTPS
- Support for multiple SSL certificates
- End-to-end SSL (re-encrypt backend traffic)

### URL-Based Routing
- Path-based routing (e.g., /images → pool1, /api → pool2)
- Multi-site hosting (different domains → different backends)
- URL rewrite capabilities

### Session Affinity
- Cookie-based session affinity
- Ensures same client routes to same backend
- Configurable per routing rule

### Web Application Firewall (WAF)
- OWASP Core Rule Set (CRS) 3.0/3.1/3.2
- Custom rules (allow/block based on conditions)
- Bot protection
- Rate limiting

## Resource Lifecycle

| Operational State | Description | Allowed Operations |
|--------------------|-------------|-------------------|
| Running | Fully operational | All operations |
| Stopped | Gateway stopped | Start, modify config |
| Starting | Starting gateway | Wait |
| Stopping | Stopping gateway | Wait |

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| Resource Group | Yes | `azure-resource-ops` |
| VNet | Yes | `azure-network-ops` |
| Dedicated Subnet | Yes (min 32 IPs) | `azure-network-ops` |
| Public IP (optional) | For public LB | `azure-network-ops` |
| Backend servers | Yes | Depends on type |

## Best Practices

### High Availability
- Use Standard_v2 or WAF_v2 SKU
- Deploy across Availability Zones
- Configure multiple backend servers
- Enable autoscaling

### Security
- Enable WAF in Prevention mode
- Use OWASP CRS 3.2
- Configure custom WAF rules for specific threats
- Enable SSL termination with strong TLS
- Use end-to-end SSL for sensitive backends

### Performance
- Enable autoscaling for variable traffic
- Configure appropriate instance count
- Use connection draining for graceful updates
- Monitor backend health

## Pricing Model

- **Pricing type**: Capacity units + data processed
- **Key dimensions**: Instance count, capacity units, data processed
- **Free tier**: None
- **Estimator**: https://azure.microsoft.com/pricing/calculator/

## Common Patterns

### Pattern 1: Web Application with SSL
- Use case: HTTPS web application
- Architecture: AGW → SSL termination → Backend servers
- Steps:
  1. Create VNet with dedicated AGW subnet
  2. Create Public IP
  3. Create Application Gateway with SSL cert
  4. Configure backend pool (FQDN or IPs)
  5. Create HTTPS listener
  6. Configure routing rule

### Pattern 2: Multi-Site Hosting
- Use case: Multiple domains on same gateway
- Architecture: AGW → Different backends per domain
- Steps:
  1. Create Application Gateway
  2. Add multiple SSL certificates
  3. Create listeners for each domain
  4. Create backend pools for each site
  5. Configure routing rules per domain

### Pattern 3: API Gateway with WAF
- Use case: Secure API endpoints
- Architecture: AGW with WAF → API backends
- Steps:
  1. Create WAF_v2 Application Gateway
  2. Create WAF policy (OWASP CRS)
  3. Add custom rules for API protection
  4. Configure path-based routing (/api/v1, /api/v2)
  5. Enable rate limiting

### Pattern 4: Blue-Green Deployment
- Use case: Zero-downtime deployments
- Architecture: AGW → Backend pool with weighted distribution
- Steps:
  1. Create new backend pool with updated servers
  2. Add to routing rule with low weight
  3. Gradually increase weight
  4. Remove old backend pool after transition