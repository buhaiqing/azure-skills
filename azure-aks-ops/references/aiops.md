# AIOps — Azure Kubernetes Service RCA Rules

> AIOps-driven root cause analysis for AKS cluster anomalies.

## Detection Signals

| Signal | Source | Description |
|--------|--------|-------------|
| pod_pending | `kubectl get pods --field-selector status.phase=Pending` | Pod stuck in Pending state |
| pod_crashloop | `kubectl get pods --field-selector status.phase=CrashLoopBackOff` | Pod crashing repeatedly |
| image_pull_fail | `kubectl describe pod` events | ImagePullBackOff error |
| node_not_ready | `kubectl get nodes` | Node in NotReady state |
| oom_killed | `kubectl describe pod` | Container OOMKilled |

## RCA Rules

### Rule: Pod Pending Diagnosis
```
trigger: pod_pending
flow:
  1. Describe pod: kubectl describe pod <name> -n <ns> | grep "Events:"
  2. Check common causes:
     - Insufficient CPU/memory: check node resources (kubectl top nodes)
     - PersistentVolumeClaim not bound: kubectl get pvc -n <ns>
     - Node selector / taint mismatch: kubectl describe node <node>
  3. Recommend: adjust resource requests / remove taints / create PVC
```

### Rule: CrashLoopBackOff Investigation
```
trigger: pod_crashloop
flow:
  1. Check pod logs: kubectl logs <pod> -n <ns> --previous
  2. Check pod events: kubectl describe pod <pod> -n <ns>
  3. Common causes:
     - Application crash: check logs for error stack
     - OOMKilled: increase memory limits
     - Liveness probe failure: check probe configuration
     - Config/secret missing: kubectl get configmap,secret -n <ns>
```

### Rule: ImagePullBackOff Handling
```
trigger: image_pull_fail
flow:
  1. Check image name and tag: kubectl describe pod <pod> -n <ns>
  2. Check if image exists in ACR: az acr repository show-tags --name <acr> --repository <repo>
  3. If image not found: check deployment yaml for correct tag
  4. If auth issue: check ACR pull secret: kubectl get secret -n <ns>
  5. If ACR not attached to AKS: az aks check-acr --name <aks> --resource-group <rg>
```

### Rule: Node NotReady Recovery
```
trigger: node_not_ready
flow:
  1. Describe node: kubectl describe node <node>
  2. Check node conditions: MemoryPressure, DiskPressure, PIDPressure
  3. Check if node is reachable: az vm get-instance-view --resource-group <mc_rg> --name <node>
  4. If resource pressure: cordon and drain before scaling
  5. If VM stopped/deallocated: az vm start --resource-group <mc_rg> --name <node>
```

### Rule: OOMKilled Recovery
```
trigger: oom_killed
flow:
  1. Check container memory usage before OOM: kubectl top pod <pod> -n <ns> --containers
  2. Check memory limits in deployment: kubectl get deployment <deploy> -n <ns> -o yaml
  3. If limits too low: recommend increasing memory limits
  4. If memory leak suspected: recommend enabling memory profiling

## Cross-Skill Integration

See `docs/cross-skill-rca-schema.md` for standard diagnostic paths and cross-service root cause analysis chains.

When this skill detects an anomaly that may involve other services:
- Delegate to `azure-monitor-ops` for metric correlation and Activity Log investigation
- Follow the standard diagnostic path defined in `docs/cross-skill-rca-schema.md`
```