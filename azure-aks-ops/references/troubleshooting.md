# AKS Troubleshooting Guide

## Common API Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| InvalidParameter | 400 | Request validation failed | Fix args per Azure REST API docs |
| InvalidParameterValue | 400 | VM size or version invalid | Check supported VM sizes and K8s versions |
| MissingParameter | 400 | Required field omitted | Add missing parameter |
| AccessDenied | 403 | RBAC permission insufficient | HALT; user updates RBAC role |
| AuthorizationFailed | 403 | Operation not permitted | HALT; check RBAC assignment |
| ResourceNotFound | 404 | Cluster or node pool not found | Verify cluster name and resource group |
| NotFound | 404 | Subscription/resource group not found | Verify subscription ID |
| Conflict | 409 | Cluster already exists or state conflict | Check current state |
| QuotaExceeded | 400/402 | VM quota limit reached | HALT; user requests quota increase |
| ServiceQuotaExceededException | 400 | Cluster/node pool limit | HALT; request support ticket |
| ThrottlingException | 429 | Rate limit exceeded | Retry with exponential backoff |
| RequestLimitExceeded | 429 | Too many requests | Backoff; reduce request rate |
| InternalError | 500 | Azure service error | Retry 3x; HALT with correlation ID |
| ServiceUnavailable | 503 | Service temporarily down | Retry 3x; HALT |
| VMSizeNotAvailable | 400 | VM size not available in location | Suggest alternative VM size |
| InsufficientCapacity | 500 | Azure capacity unavailable | Try different location or VM size |

## Diagnostic Order

### Cluster-Level Issues

1. **Verify credentials**: `az account show`
2. **Verify subscription**: Check `AZURE_SUBSCRIPTION_ID`
3. **Verify resource group**: `az group show --name {{rg}}`
4. **Get cluster status**: `az aks show --name {{aks}} --resource-group {{rg}}`
5. **Check provisioning state**: Review cluster show output
6. **Check Activity Log**: `az monitor activity-log list`
7. **Check node status**: `kubectl get nodes`

### Node Pool Issues

1. **List node pools**: `az aks nodepool list --cluster-name {{aks}} --resource-group {{rg}}`
2. **Get node pool details**: `az aks nodepool show --cluster-name {{aks}} --resource-group {{rg}} --name {{pool}}`
3. **Check node VM status**: Review VM status via `az vm list`
4. **Check node count**: Compare actual vs. expected node count

## Cluster Provisioning Issues

### Issue: Cluster stuck in "Creating"

**Symptoms**:
- AKS cluster provisioning state stuck at "Creating"
- Long wait time (> 30 minutes)

**Diagnosis Steps**:
1. Check cluster status: `az aks show --name {{aks}} --resource-group {{rg}} --output json`
2. Check Activity Log: `az monitor activity-log list --resource {{aks-resource-id}}`
3. Verify VNet/subnet if using Azure CNI
4. Check VM availability: `az vm list-skus --location {{location}}`

**Resolution Options**:
- Option A: Wait longer ( some complex configs take more time)
- Option B: Check Activity Log for specific error
- Option C: If VNet issue, verify subnet delegation
- Option D: Cancel and retry with different config

### Issue: Cluster creation failed

**Symptoms**:
- Provisioning state shows "Failed"
- Error message in Activity Log

**Common Causes**:
| Cause | Resolution |
|-------|------------|
| VNet/subnet not found | Verify VNet exists in same RG and location |
| Subnet delegation missing | Add Microsoft.ContainerService/managedClusters delegation |
| VM size unavailable | Use different VM size |
| Quota exceeded | Request quota increase |
| DNS prefix conflict | Use unique DNS prefix |

**Diagnosis Steps**:
```bash
# Check Activity Log for detailed error
az monitor activity-log list \
  --resource "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.ContainerService/managedClusters/{{aks}}" \
  --output json

# Verify dependencies
az network vnet show --name {{vnet}} --resource-group {{rg}}
az network vnet subnet show --vnet-name {{vnet}} --resource-group {{rg}} --name {{subnet}}
```

## Node Pool Issues

### Issue: Node pool scaling failed

**Symptoms**:
- Node count not matching target
- Scaling operation stuck or failed

**Diagnosis Steps**:
1. Check node pool state: `az aks nodepool show --cluster-name {{aks}} --resource-group {{rg}} --name {{pool}}`
2. Check VM quota: `az vm list-skus --location {{location}}`
3. Check VM availability in region
4. Verify VM size is valid

**Resolution Options**:
- Option A: Request quota increase if quota issue
- Option B: Use different VM size if availability issue
- Option C: Check if autoscaler conflicts ( disable autoscaler during manual scale)

### Issue: Node pool nodes not ready

**Symptoms**:
- Nodes show `NotReady` status in kubectl
- Pods failing to schedule

**Diagnosis Steps**:
```bash
# Check node status
kubectl get nodes
kubectl describe node {{node-name}}

# Check node conditions
kubectl get nodes -o custom-columns=NAME:.metadata.name,STATUS:.status.conditions[-1].type
```

**Common Causes**:
| Cause | Resolution |
|-------|------------|
| Network configuration issue | Check VNet/subnet config |
| DNS resolution failure | Check DNS settings |
| Insufficient resources | Scale up node pool |
| Node VM issues | Check VM health via Azure portal |

## Network Issues

### Issue: Pods cannot communicate

**Symptoms**:
- Pod-to-pod communication fails
- Service endpoints unreachable

**Diagnosis Steps**:
1. Check network policy configuration
2. Verify network plugin (kubenet vs azure CNI)
3. Check pod IP assignment
4. Verify NSG rules on subnet

```bash
# Check pod IPs
kubectl get pods -o wide

# Test connectivity
kubectl exec -it {{pod}} -- ping {{other-pod-ip}}
```

**Resolution Options**:
- Option A: Review network policies
- Option B: Check NSG rules on subnet
- Option C: Verify VNet peering if cross-VNet
- Option D: Check if using correct network plugin

### Issue: Private cluster API server unreachable

**Symptoms**:
- Cannot connect to API server
- kubectl commands fail

**Diagnosis Steps**:
1. Verify private cluster configuration
2. Check authorized IP ranges if enabled
3. Verify network connectivity to private endpoint

**Resolution Options**:
- Option A: Connect via authorized network
- Option B: Use private endpoint
- Option C: Disable authorized IP ranges temporarily

## Upgrade Issues

### Issue: Cluster upgrade failed

**Symptoms**:
- Upgrade stuck or failed
- Version mismatch between nodes

**Diagnosis Steps**:
```bash
# Check current version
az aks show --name {{aks}} --resource-group {{rg}} --query "kubernetesVersion"

# Check available upgrades
az aks get-upgrades --name {{aks}} --resource-group {{rg}} --output json
```

**Resolution Options**:
- Option A: Verify target version is supported
- Option B: Check node health before upgrade
- Option C: Ensure node pools can be upgraded
- Option D: Retry upgrade operation

### Issue: Node pool version mismatch

**Symptoms**:
- Node pool on different K8s version than control plane
- Version drift warnings

**Resolution**:
```bash
# Upgrade node pool
az aks nodepool upgrade \
  --cluster-name {{aks}} \
  --resource-group {{rg}} \
  --name {{pool}} \
  --kubernetes-version {{version}}
```

## Credential & Access Issues

### Issue: Cannot get cluster credentials

**Symptoms**:
- `az aks get-credentials` fails
- kubectl cannot connect

**Diagnosis Steps**:
1. Verify Azure credentials: `az account show`
2. Verify cluster exists: `az aks show`
3. Check RBAC permissions

**Resolution Options**:
| Cause | Resolution |
|-------|------------|
| No Azure RBAC permission | Add AzureKubernetesServiceClusterUserRole |
| Private cluster access issue | Connect from authorized network |
| Subscription mismatch | Verify correct subscription |

### Issue: kubectl connection refused

**Symptoms**:
- `kubectl cluster-info` fails
- Connection refused error

**Diagnosis Steps**:
1. Verify kubeconfig: `kubectl config view`
2. Check current context: `kubectl config current-context`
3. Verify API server endpoint

**Resolution Options**:
- Option A: Re-download credentials: `az aks get-credentials --overwrite-existing`
- Option B: Check private cluster access
- Option C: Verify authorized IP ranges

## Performance Issues

### Issue: Cluster slow or unresponsive

**Symptoms**:
- High latency in API calls
- Nodes under heavy load

**Diagnosis Steps**:
```bash
# Check node resource usage
kubectl top nodes
kubectl describe nodes

# Check pod resource usage
kubectl top pods -A
```

**Resolution Options**:
- Option A: Scale up node pool
- Option B: Optimize pod resource limits
- Option C: Add more node pools
- Option D: Enable autoscaling

## Activity Log for Debugging

```bash
# Check recent AKS operations
az monitor activity-log list \
  --resource-provider Microsoft.ContainerService \
  --start-time "2026-05-10T00:00:00Z" \
  --output json

# Check specific cluster operations
az monitor activity-log list \
  --resource "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.ContainerService/managedClusters/{{aks}}" \
  --output json
```

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Production cluster down | Critical | Immediate Azure support ticket |
| Data loss or corruption | Critical | Immediate support + backup review |
| Security breach indicator | Critical | Immediate support + security review |
| Upgrade failure affecting workloads | High | Support ticket with version details |
| Persistent node pool issues | High | Support ticket with node logs |
| Quota or capacity issues | Medium | Quota increase request via portal |
| Feature clarification | Low | Azure forums or documentation |

## Kubernetes-Specific Troubleshooting

```bash
# Check cluster events
kubectl get events -A --sort-by='.lastTimestamp'

# Check pod logs
kubectl logs {{pod}} -n {{namespace}}
kubectl logs {{pod}} -n {{namespace}} --previous  # Previous container instance

# Describe resources
kubectl describe pod {{pod}} -n {{namespace}}
kubectl describe deployment {{deployment}} -n {{namespace}}

# Check resource quotas
kubectl get resourcequotas -A
kubectl describe resourcequota {{quota}} -n {{namespace}}

# Check node capacity
kubectl describe nodes | grep -A 5 "Allocated resources"
```