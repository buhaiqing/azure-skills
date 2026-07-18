# Azure Virtual Machine Core Concepts

## What is Azure Virtual Machine

- **Purpose**: Scalable compute capacity (virtual servers) in the cloud
- **Category**: Compute / Infrastructure as a Service (IaaS)
- **Portal**: https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.Compute%2FVirtualMachines
- **Docs**: https://docs.microsoft.com/azure/virtual-machines/
- **Pricing**: https://azure.microsoft.com/pricing/details/virtual-machines/

## Primary Resources

| Resource | Description | Portal Path |
|----------|-------------|-------------|
| Virtual Machine | Compute instance | /Microsoft.Compute/VirtualMachines |
| VM Image | OS template (marketplace or custom) | /Microsoft.Compute/Images |
| Managed Disk | Storage attached to VM | /Microsoft.Compute/Disks |
| Network Interface | Network connectivity | /Microsoft.Network/networkInterfaces |
| Public IP | Internet-accessible IP | /Microsoft.Network/publicIPAddresses |
| Virtual Network | Network isolation | /Microsoft.Network/virtualNetworks |

## Architecture & Limits

### Resource ID Format
```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{vm-name}
```

### VM Quotas per Region

| Quota | Default | Adjustable |
|-------|---------|------------|
| Total regional vCPUs | Varies by series | Yes (support ticket) |
| Standard vCPUs | Varies | Yes |
| Spot vCPUs | Varies | Yes |
| VMs per region | Varies | Yes |

Check quotas:
```bash
az vm list-usage --location "{{location}}" --output json
```

### Naming Constraints

| Resource | Rules |
|----------|-------|
| VM Name | 1-64 chars, alphanumeric, hyphens, underscores |
| DNS Name (public IP) | 3-63 chars, lowercase alphanumeric, hyphens |
| Disk Name | 1-80 chars, alphanumeric, hyphens, underscores |

## VM Size Families

### General Purpose (Balanced CPU/Memory)

| Series | Description | Best For |
|--------|-------------|----------|
| **B-series** | Burstable, cost-effective | Dev/test, small workloads |
| **D-series** | General purpose | Enterprise apps |
| **DS-series** | Premium storage support | Production workloads |
| **DC-series** | Confidential computing | Secure workloads |

### Compute Optimized (High CPU Ratio)

| Series | Description | Best For |
|--------|-------------|----------|
| **F-series** | High CPU count | Batch processing, analytics |
| **FS-series** | Premium storage | Compute-intensive production |

### Memory Optimized (High Memory Ratio)

| Series | Description | Best For |
|--------|-------------|----------|
| **E-series** | High memory | In-memory databases, analytics |
| **ES-series** | Premium storage | Memory-intensive production |
| **M-series** | Largest memory | SAP HANA, large databases |

### Storage Optimized (High Disk I/O)

| Series | Description | Best For |
|--------|-------------|----------|
| **L-series** | High storage throughput | Big data, databases |
| **LS-series** | Premium storage | Storage-intensive production |

### GPU (Graphics/AI)

| Series | Description | Best For |
|--------|-------------|----------|
| **NC-series** | NVIDIA GPUs | AI/ML training |
| **NV-series** | NVIDIA V100 | Visualization, rendering |
| **NP-series** | AMD GPUs | GPU workloads |

### High Performance Computing

| Series | Description | Best For |
|--------|-------------|----------|
| **H-series** | High CPU performance | HPC, simulation |
| **HB-series** | AMD EPYC | HPC workloads |

## Storage Options

### Managed Disks

| Type | Performance | Use Case |
|------|-------------|----------|
| **Standard HDD** | Lowest cost, lowest performance | Dev/test, infrequent access |
| **Standard SSD** | Low cost, moderate performance | Web servers, dev/test |
| **Premium SSD** | High performance | Production, databases |
| **Ultra Disk** | Highest performance | Mission-critical, high IOPS |

### Disk Size Limits

| Type | Max Size | Max IOPS | Max Throughput |
|------|----------|----------|----------------|
| Standard HDD | 32 TB | 500 | 60 MB/s |
| Standard SSD | 32 TB | 6,000 | 750 MB/s |
| Premium SSD | 32 TB | 20,000 | 900 MB/s |
| Ultra Disk | 65 TB | 160,000 | 2,000 MB/s |

## OS Disk vs Data Disk

| Disk Type | Purpose | Typical Size |
|-----------|---------|--------------|
| **OS Disk** | Operating system | 30-127 GB default |
| **Data Disk** | Application data | Up to 32 TB each |
| **Temp Disk** | Temporary storage | VM-size dependent (ephemeral) |

## VM Images

### Marketplace Images

Find images:
```bash
# List popular images
az vm image list --output json

# Search for specific image
az vm image list --publisher Canonical --offer UbuntuServer --sku 22_04-lts --output json

# List all images in location
az vm image list --location "{{location}}" --output json
```

### Custom Images

- Create from existing VM
- Store in Managed Image resource
- Use for consistent deployments
- Share across subscriptions via Shared Image Gallery

## Network Configuration

### Network Interface (NIC)

| Feature | Description |
|---------|-------------|
| **Private IP** | VNet internal IP |
| **Public IP** | Internet-accessible IP |
| **DNS Name** | Optional DNS label |
| **Accelerated Networking** | High-performance networking |
| **NIC Security Groups** | Network security rules |

### Virtual Network Integration

| Option | Description |
|--------|-------------|
| **Basic VNet** | Simple VM in subnet |
| **Multiple NICs** | Multiple network interfaces |
| **VNet Peering** | Cross-VNet connectivity |
| **Private Endpoint** | Private connectivity to PaaS |

## VM Power States

| State | Billing | Description |
|-------|---------|-------------|
| **Creating** | Yes | VM provisioning in progress |
| **Starting** | Yes | VM starting up |
| **Running** | Yes | VM fully operational |
| **Stopping** | Yes | VM shutting down |
| **Stopped** | Yes | VM stopped (still billed) |
| **Deallocating** | No | Releasing compute resources |
| **Deallocated** | No | VM stopped, billing stopped |
| **Updating** | Yes | Configuration update |

**Important**: Use `az vm stop` (deallocate) to stop billing, not just power off.

## Availability Features

### Availability Sets

- Logical grouping of VMs
- Provides fault isolation (FD) and update isolation (UD)
- Up to 3 fault domains, 5 update domains
- Legacy HA feature (use Zones instead)

### Availability Zones

- Physical separation within region
- Zone-redundant VMs
- Higher SLA (99.99%)
- Recommended for production

### Spot VMs

- Discounted pricing (up to 90% off)
- May be evicted when Azure needs capacity
- Use for fault-tolerant, batch workloads

## VM Extensions

Common extensions:
| Extension | Purpose |
|-----------|---------|
| **VMAccessAgent** | Reset password/SSH |
| **CustomScript** | Run scripts on VM |
| **AzureMonitorAgent** | Monitoring integration |
| **AzureDiskEncryption** | Disk encryption |

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| Resource Group | Yes | `azure-resource-ops` |
| Virtual Network | Yes (or create with VM) | `azure-network-ops` |
| Subnet | Yes (or create with VM) | `azure-network-ops` |
| Network Interface | Yes (created with VM) | `azure-network-ops` |
| Public IP | Optional | `azure-network-ops` |
| Managed Disk | Yes (created with VM) | `azure-disk-ops` |

## Best Practices

### High Availability
- Use Availability Zones for production
- Deploy multiple VMs for redundancy
- Use load balancers for traffic distribution
- Configure auto-scaling

### Security
- Use SSH keys for Linux (not passwords)
- Apply NSG rules to restrict access
- Enable disk encryption
- Keep OS updated
- Use Azure Defender

### Performance
- Choose appropriate VM size
- Use Premium SSD for production
- Enable accelerated networking
- Optimize application configuration

### Cost Optimization
- Use Spot VMs for batch workloads
- Resize underutilized VMs
- Deallocate stopped VMs
- Use Reserved Instances for stable workloads

## Pricing Model

- **Pricing type**: Pay-per-use + Reserved Instances
- **Key dimensions**: VM size, OS license, region, duration
- **Free tier**: Limited VM hours in Azure Free Account
- **Spot pricing**: Up to 90% discount for eviction-tolerant workloads
- **Estimator**: https://azure.microsoft.com/pricing/calculator/

## Common Patterns

### Pattern 1: Web Server
- Use case: Public web application
- Architecture: Linux VM + Premium SSD + Public IP + NSG
- Steps:
  1. Create VM with Ubuntu image
  2. Configure public IP with DNS
  3. Open HTTP/HTTPS ports in NSG
  4. Install web server software

### Pattern 2: Multi-tier Application
- Use case: Enterprise application with tiers
- Architecture: Multiple VMs + Internal LB + VNet
- Steps:
  1. Create VNet with subnets per tier
  2. Create VMs in each subnet
  3. Configure internal load balancer
  4. Implement security groups

### Pattern 3: Dev/Test Environment
- Use case: Development and testing
- Architecture: B-series VM + Standard SSD + Auto-shutdown
- Steps:
  1. Create cost-effective B-series VM
  2. Configure auto-shutdown schedule
  3. Use Standard SSD
  4. Implement spot VMs where appropriate

### Pattern 4: High-performance Compute
- Use case: HPC, simulations
- Architecture: H-series VM + Premium/Ultra Disk + Accelerated Networking
- Steps:
  1. Create H-series VM
  2. Configure Ultra Disk for high IOPS
  3. Enable accelerated networking
  4. Optimize for workload

## Common VM Sizes (Quick Reference)

| Size | vCPUs | Memory | Use Case |
|------|-------|--------|----------|
| **Standard_B2s** | 2 | 4GB | Dev/test |
| **Standard_DS2_v2** | 2 | 7GB | Small production |
| **Standard_DS3_v2** | 4 | 14GB | Medium production |
| **Standard_D4s_v3** | 4 | 16GB | General purpose |
| **Standard_E2s_v3** | 2 | 16GB | Memory-intensive |
| **Standard_F2s_v2** | 2 | 4GB | Compute-intensive |

## Common VM Images (Quick Reference)

| Image | Publisher | Offer | SKU |
|-------|-----------|-------|-----|
| Ubuntu 22.04 LTS | Canonical | UbuntuServer | 22_04-lts |
| Ubuntu 20.04 LTS | Canonical | UbuntuServer | 20_04-lts |
| Windows Server 2022 | MicrosoftWindowsServer | WindowsServer | 2022-datacenter |
| Windows Server 2019 | MicrosoftWindowsServer | WindowsServer | 2019-datacenter |
| CentOS 8 | OpenLogic | CentOS | 8_5 |
| Debian 11 | Debian | Debian | 11 |
| RHEL 8 | RedHat | RHEL | 8_8 |

## Remote Command Execution (Cloud Assistant)

| Method | Description | Use Case |
|--------|-------------|----------|
| **RunCommand** | One-time command execution | Quick diagnostics, one-off tasks |
| **VM Extension** | Persistent agent with scripts | Long-running config, monitoring |
| **SSH/RDP** | Direct interactive access | Full interactive session |

### Available RunCommand IDs

| OS | Command ID | Description |
|----|------------|-------------|
| **Linux** | RunShellScript | Execute bash shell script |
| **Linux** | RunPowerShellScript | Execute PowerShell (if installed) |
| **Linux** | ifconfig | Network interface info |
| **Windows** | RunPowerShellScript | Execute PowerShell script |