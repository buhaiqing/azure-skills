# Azure Load Balancer Core Concepts

## What is Azure Load Balancer

- **Purpose**: Layer 4 (L4) load balancing for TCP/UDP traffic
- **Category**: Network / Load Balancing
- **Portal**: https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.Network%2FloadBalancers
- **Docs**: https://docs.microsoft.com/azure/load-balancer/
- **Pricing**: https://azure.microsoft.com/pricing/details/load-balancer/

## Primary Resources

| Resource | Description | Portal Path |
|----------|-------------|-------------|
| Load Balancer | L4 load balancer resource | /Microsoft.Network/loadBalancers |
| Frontend IP | Entry point (public or internal) | Frontend IP configuration |
| Backend Pool | Target VMs/NICs | Backend address pool |
| Health Probe | Health check mechanism | Health probe |
| Load Balancing Rule | Traffic distribution rule | Load balancing rule |
| Inbound NAT Rule | Port forwarding to specific VM | Inbound NAT rule |
| Outbound Rule | Outbound SNAT configuration | Outbound rule |

## Architecture & Limits

### Resource ID Format
```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Network/loadBalancers/{lb-name}
```

### SKU Comparison

| Feature | Basic SKU | Standard SKU |
|---------|-----------|--------------|
| Backend pool size | Up to 100 VMs | Up to 1000 VMs |
| Health probes | Limited | Full HTTP/TCP probes |
| HA ports | Not supported | Supported |
| Zone redundancy | Not supported | Zone-redundant |
| Outbound rules | Not supported | Supported |
| SLA | None | 99.99% SLA |

### Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| Load Balancers per region | 100 | Yes (support ticket) |
| Backend pool members | 100 (Basic), 1000 (Standard) | Yes |
| Rules per LB | 300 | Yes |
| Health probes per LB | 100 | Yes |

### Supported Protocols
- TCP
- UDP
- HA Ports (Standard SKU only, all ports)

## Load Balancer Types

### Public Load Balancer
- Entry point: Public IP address
- Use case: Internet-facing services
- Frontend: Public IP resource
- Backend: VMs with public IP or NIC in backend pool

### Internal Load Balancer
- Entry point: Private IP in VNet
- Use case: Internal services, multi-tier apps
- Frontend: Private IP in subnet
- Backend: VMs in same VNet

## Resource Lifecycle

| Provisioning State | Description | Allowed Operations |
|--------------------|-------------|-------------------|
| Updating | Configuration change | Limited |
| Succeeded | Operational | All operations |
| Failed | Terminal error state | Delete or retry |

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| Resource Group | Yes | `azure-resource-ops` |
| Public IP (for public LB) | Yes | `azure-network-ops` |
| VNet + Subnet (for internal LB) | Yes | `azure-network-ops` |
| VMs/NICs for backend | Yes | `azure-vm-ops` |

## Best Practices

### High Availability
- Use Standard SKU for production
- Deploy across Availability Zones
- Configure multiple backend VMs
- Use zone-redundant Public IP

### Security
- Use Network Security Groups (NSG)
- Limit exposed ports
- Use internal LB for internal services
- Configure proper NSG rules on backend subnet

### Performance
- Use HA ports for internal traffic
- Distribute backend VMs across zones
- Configure appropriate health probe interval
- Monitor backend VM capacity

## Pricing Model

- **Pricing type**: Pay-per-use + data processed
- **Key dimensions**: Rules, data processed, HA ports
- **Free tier**: Basic SKU has limited free tier
- **Estimator**: https://azure.microsoft.com/pricing/calculator/

## Common Patterns

### Pattern 1: Public Web Service
- Use case: Internet-facing web servers
- Architecture: Public LB → Multiple VMs in backend pool
- Steps:
  1. Create Public IP
  2. Create Public Load Balancer
  3. Configure health probe (HTTP on port 80)
  4. Create load balancing rule
  5. Add VM NICs to backend pool

### Pattern 2: Internal Service Tier
- Use case: Database, internal API services
- Architecture: Internal LB → Backend VMs in VNet
- Steps:
  1. Create VNet and subnet
  2. Create Internal Load Balancer with private IP
  3. Configure health probe
  4. Create load balancing rule
  5. Add backend VM NICs

### Pattern 3: Port Forwarding (NAT)
- Use case: SSH/RDP access to specific VMs
- Architecture: Public LB → Inbound NAT rules
- Steps:
  1. Create Public LB
  2. Create inbound NAT rule for each VM
  3. Map frontend port to backend VM port
  4. Assign NIC to NAT rule