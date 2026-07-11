# Azure Container Instances Core Concepts

## What is Azure Container Instances (ACI)

- **Purpose**: Run containers directly on Azure with no VM/orchestrator management; per-second billing.
- **Category**: Compute / Serverless Containers (PaaS)
- **Docs**: https://docs.microsoft.com/azure/container-instances/
- **Pricing**: https://azure.microsoft.com/pricing/details/container-instances/

## Primary Resources

| Resource | Description | Provider Path |
|----------|-------------|---------------|
| Container Group | Scheduling unit; 1+ containers sharing network/IP/lifecycle | Microsoft.ContainerInstance/containerGroups |
| Container | A single image instance inside the group | child of container group |
| Volume (mount) | Empty dir / Azure File / secret / gitRepo | container `volumeMounts` |

## Architecture

```
Container Group (1 IP, 1 lifecycle, shared volume)
├── Container A (image, cpu, memory)
├── Container B (image, cpu, memory)
└── Volume mount (Azure File / emptyDir / secret)
```

- All containers in a group are scheduled on the same host, share an IP and port namespace.
- A container group is **immutable after creation**: changing image/cpu/memory requires **delete + recreate** (update is limited to restart policy / tags).

### Resource ID Format
```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.ContainerInstance/containerGroups/{cg-name}
```

## Key Properties

| Property | Meaning | Values |
|----------|---------|--------|
| `osType` | Host OS | `Linux` (default) / `Windows` |
| `restartPolicy` | When to restart finished containers | `Always` / `OnFailure` / `Never` |
| `ipAddress.type` | Network exposure | `Public` / `Private` (VNet injection) |
| `ipAddress.ports` | Exposed ports | list of `{port, protocol}` |
| `sku` | Billing tier | `Standard` / `Confidential` |

## Compute Limits (per container)

| Dimension | Note |
|-----------|------|
| CPU | Request per container (e.g. 1.0, 2.0). Max varies by region/OS. |
| Memory | `memory_in_gb`, e.g. `1.5`. GPU SKU adds `gpu` count. |
| GPU | `gpu` count + `gpuSku` (`K80`/`P100`/`V100`/`T4`/`A100`); limited regions. |

> Quota: regional vCPU quota applies. Check with `az container list-usage --location {{user.location}}` (TE-1: query, don't hardcode).

## Image Registry & Auth

| Source | Auth | Skill |
|--------|------|-------|
| Docker Hub / MCR (public) | None | — |
| Azure Container Registry | `--registry-login-server/--username/--password` or managed identity | delegate `azure-acr-ops` for registry ops |
| Other private registry | `--registry-*` flags | delegate `azure-acr-ops` if auth/token issues |

**Never inline secrets**: pass `--registry-password "{{env.REGISTRY_PASSWORD}}"` or delegate credential handling to `azure-acr-ops`.

## Networking

| Mode | CLI | Notes |
|------|-----|-------|
| Public IP | `--ip-address public` (default) | ACI assigns a public IP; DNS label via `--dns-name-label` |
| Private (VNet) | `--subnet` / `--vnet` | VNet/subnet design → delegate `azure-vnet-ops` / `azure-privateendpoint-ops` |

## Volumes

| Type | Use |
|------|-----|
| `emptyDir` | Scratch space, shared across containers in the group |
| `azureFile` | Persistent file share (Azure Storage) |
| `secret` | Inject secret files from key vault-like values |
| `gitRepo` | Clone a git repo into the volume |

## Restart Policies

| Policy | Behavior |
|--------|----------|
| `Always` | Restart on exit (long-running services) |
| `OnFailure` | Restart only on non-zero exit (batch jobs) |
| `Never` | Run once; leave stopped on completion |

## State / Lifecycle

| State | Meaning |
|-------|---------|
| `Pending` | Provisioning |
| `Running` | Containers running |
| `Succeeded` | All containers exited 0 (with `OnFailure`/`Never`) |
| `Failed` | A container exited non-zero or image pull failed |
| `Stopped` | Group stopped via `az container stop` |

## Dependencies

| Dependency | Required | Delegate to |
|------------|----------|-------------|
| Resource Group | Yes | `azure-resource` (create via `az group create`) |
| Container Registry / image push | For private images | `azure-acr-ops` |
| VNet / Private Endpoint | For private networking | `azure-vnet-ops` / `azure-privateendpoint-ops` |
| Managed Identity for ACR pull | Optional | `azure-acr-ops` (auth) |

## Common Patterns

### Pattern 1: Scheduled batch job
- `restartPolicy: OnFailure`, single container, exits after work done.

### Pattern 2: Public web front-end
- `ipAddress.type: Public`, expose port 80/443, `restartPolicy: Always`.

### Pattern 3: Multi-container (sidecar)
- Main app + logging sidecar sharing an `emptyDir` volume.

## Best Practices

- Right-size CPU/memory; per-second billing rewards tight limits.
- Use `OnFailure`/`Never` for jobs to avoid runaway restart loops.
- For private images, prefer managed identity over password; delegate registry auth to `azure-acr-ops`.
- Immutable groups: plan changes as delete+recreate, not in-place update.
- Use Azure File volumes for state that must survive a restart.
