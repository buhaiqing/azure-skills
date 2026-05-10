# Azure Kubernetes Service (AKS) Core Concepts

## What is Azure Kubernetes Service (AKS)

- **Purpose**: Managed Kubernetes service for container orchestration
- **Category**: Compute / Containers / Orchestration
- **Portal**: https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.ContainerService%2FmanagedClusters
- **Docs**: https://docs.microsoft.com/azure/aks/
- **Pricing**: https://azure.microsoft.com/pricing/details/kubernetes-service/

## Primary Resources

| Resource | Description | Portal Path |
|----------|-------------|-------------|
| Managed Cluster | AKS cluster resource | /Microsoft.ContainerService/managedClusters |
| Node Pool | Group of worker nodes | Agent pools in cluster |
| kubeconfig | Cluster access credentials | Downloadable from cluster |
| Namespace | Kubernetes namespace | K8s resource |
| Deployment | K8s deployment | K8s resource |
| Pod | Container instance | K8s resource |
| Service | K8s service | K8s resource |

## Architecture & Limits

### Resource ID Format
```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.ContainerService/managedClusters/{aks-name}
```

### Cluster Tiers

| Tier | Description | Use Case |
|------|-------------|----------|
| **Free** | No SLA, basic features | Dev/test, learning |
| **Standard** | SLA, enterprise features | Production workloads |
| **Premium** | Full enterprise features | Mission-critical apps |

### Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| Max clusters per region | 100 | Yes (support ticket) |
| Max node pools per cluster | 100 | Yes |
| Max nodes per node pool | 1000 | Yes |
| Max total nodes per cluster | 5000 | Yes |

### Supported Kubernetes Versions

AKS supports multiple Kubernetes versions. Check available versions:

```bash
az aks get-versions --location "{{user.location}}" --output json
```

- Generally supports N-2 versions (current + 2 previous)
- Automatic upgrades available ( Planned maintenance )
- Always check latest supported version before creation

## Node Pool Types

### System Node Pool
- Runs critical system pods (CoreDNS, metrics-server, etc.)
- Minimum 1 system node pool required
- Recommended: 2-3 nodes for reliability
- Mode: `System`

### User Node Pool
- Runs user workloads
- Can have multiple user node pools
- Can scale independently
- Mode: `User`

### Spot Node Pool
- Uses Azure Spot VMs (discounted, may be evicted)
- Best for batch jobs, fault-tolerant workloads
- Mode: `User` with spot VMs

## Networking Models

### Kubenet (Basic)
- Basic Kubernetes networking
- No VNet integration required
- Pods use overlay network
- Use case: Simple dev/test, limited VNet requirements

### Azure CNI (Advanced)
- Pods get IPs from VNet subnet
- Full VNet integration
- Network policies supported
- Use case: Production, VNet integration, enterprise security

### Network Policy Options

| Policy Engine | Description |
|---------------|-------------|
| **Calico** | Open-source, full features |
| **Azure** | Azure-native, simplified |
| **Cilium** | eBPF-based, high performance |

## Identity & Security

### Managed Identity

| Type | Description |
|------|-------------|
| **System-assigned** | Created with cluster, tied to cluster lifecycle |
| **User-assigned** | Pre-created, independent lifecycle |

### RBAC Options

- **Azure AD Integration**: Use Azure AD for K8s RBAC
- **Kubernetes RBAC**: Native K8s RBAC
- **Combined**: Both Azure AD and K8s RBAC

### Security Features

| Feature | Description |
|---------|-------------|
| **Private Cluster** | API server not publicly accessible |
| **Authorized IP Ranges** | Restrict API server access |
| **Azure Policy** | Enforce compliance on K8s resources |
| **Microsoft Defender** | Security monitoring and threat detection |

## Addons & Integrations

### Built-in Addons

| Addon | Description | Enable Command |
|-------|-------------|----------------|
| **monitoring** | Azure Monitor for containers | `--enable-addons monitoring` |
| **http-app-routing** | HTTP ingress with DNS | `--enable-addons http_application_routing` |
| **azure-keyvault-secrets-provider** | Key Vault secrets in pods | `--enable-addons azure-keyvault-secrets-provider` |
| **azure-policy** | Azure Policy enforcement | `--enable-addons azure-policy` |

### Common Integrations

| Integration | Purpose |
|-------------|---------|
| Azure Container Registry (ACR) | Private container image storage |
| Azure Monitor | Logging and metrics |
| Azure Key Vault | Secrets management |
| Azure App Gateway Ingress | L7 ingress controller |
| Azure Storage | Persistent volumes |

## Resource Lifecycle

| Provisioning State | Description | Allowed Operations |
|--------------------|-------------|-------------------|
| Creating | Cluster provisioning | None (wait) |
| Succeeded | Operational | All operations |
| Updating | Configuration change | Limited |
| Deleting | Deletion in progress | None |
| Failed | Terminal error state | Delete or retry |

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| Resource Group | Yes | `azure-resource-ops` |
| Virtual Network (azure CNI) | Yes | `azure-network-ops` |
| Subnet (azure CNI) | Yes | `azure-network-ops` |
| Azure Container Registry | Optional | `azure-acr-ops` |
| Azure Monitor | Optional | `azure-monitor-ops` |
| Azure Key Vault | Optional | `azure-keyvault-ops` |

## Best Practices

### High Availability
- Deploy across Availability Zones (when supported)
- Use Standard tier for production
- Minimum 3 nodes in system node pool
- Use multiple user node pools for workload separation

### Security
- Enable Azure AD integration for RBAC
- Use private clusters for sensitive workloads
- Enable Microsoft Defender for Containers
- Use Azure Policy for compliance
- Restrict API server access with authorized IP ranges

### Performance
- Choose appropriate VM size for workloads
- Use node pool autoscaler
- Implement horizontal pod autoscaler (HPA)
- Use cluster autoscaler for dynamic scaling

### Cost Optimization
- Use spot node pools for fault-tolerant workloads
- Implement proper resource limits in pods
- Scale down during low usage periods
- Use reserved capacity for stable workloads

## Pricing Model

- **Pricing type**: Free tier + paid tiers (Standard/Premium)
- **Key dimensions**: Node VMs, tier, addons
- **Free tier**: No management fee, pay for VMs only (no SLA)
- **Standard tier**: Management fee + VM cost (SLA)
- **Estimator**: https://azure.microsoft.com/pricing/calculator/

## Common Deployment Patterns

### Pattern 1: Simple Dev/Test Cluster
- Use case: Development, testing, learning
- Architecture: Single node pool, kubenet networking
- Steps:
  1. Create basic cluster with kubenet
  2. Get credentials
  3. Deploy test applications

### Pattern 2: Production Web Application
- Use case: Production web services
- Architecture: Azure CNI, multiple node pools, monitoring, ACR integration
- Steps:
  1. Create VNet and subnet
  2. Create ACR for images
  3. Create AKS with azure CNI
  4. Enable monitoring addon
  5. Integrate with ACR
  6. Deploy application

### Pattern 3: Private Enterprise Cluster
- Use case: Secure enterprise workloads
- Architecture: Private cluster, Azure AD RBAC, Azure Policy, Key Vault
- Steps:
  1. Create private cluster with authorized IPs
  2. Enable Azure AD integration
  3. Enable Azure Policy addon
  4. Configure Key Vault secrets provider
  5. Deploy with enterprise governance

### Pattern 4: Multi-zone High Availability
- Use case: Mission-critical applications
- Architecture: Zone-redundant node pools, Standard tier
- Steps:
  1. Create Standard tier cluster
  2. Configure zone-redundant node pools
  3. Enable autoscaling
  4. Deploy with pod anti-affinity

## kubectl Cheat Sheet

```bash
# Cluster info
kubectl cluster-info
kubectl get nodes
kubectl get namespaces

# Deployments
kubectl create deployment NAME --image=IMAGE
kubectl scale deployment NAME --replicas=N
kubectl set image deployment/NAME CONTAINER=IMAGE:VERSION

# Services
kubectl expose deployment NAME --port=PORT --type=TYPE
kubectl get services

# Logs & Debug
kubectl logs POD_NAME
kubectl describe pod POD_NAME
kubectl exec -it POD_NAME -- /bin/bash

# Config
kubectl config get-contexts
kubectl config use-context CONTEXT_NAME
kubectl config current-context
```