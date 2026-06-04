# Rubric — azure-aks-ops

> GCL rubric for Azure Kubernetes Service (AKS) operations.
> See `AGENTS.md §3` for dimension definitions and thresholds.

## Dimensions

| Dimension | Scale | Default threshold | Destructive threshold (delete/stop/scale-to-0/upgrade) |
|-----------|-------|-------------------|--------------------------------------------------------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Safety** | 0 / 1 | = 1 | = 1 |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |

**Safety = 0 → ABORT immediately.**

## Operation-Specific Scoring Guidance

### Create AKS Cluster
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Cluster created with correct name/RG/location/node count; provisioning = Succeeded | Cluster created but node count mismatch | Cluster not created or wrong subscription |
| Safety | Pre-flight all passed; `--enable-managed-identity` used | Pre-flight partially done | No pre-flight checks |
| Idempotency | Retry with same params idempotent; `az aks show` confirms existing | Retry shows conflict but safe | Retry creates duplicate resources |
| Traceability | Full command + stdout + stderr + `az aks show` verify | Partial capture | No trace saved |
| Spec Compliance | Follows `core-concepts.md` + `azure-cli-conventions.md` | Minor deviation | Hallucinated flag or missing RG |

### Delete AKS Cluster
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Cluster deleted; `az aks show` confirms `ResourceNotFound` | Wrong cluster shown first | Wrong cluster deleted |
| Safety | Explicit human confirmation exact cluster name; `az aks show` before delete; impact (workload, IPs, etc.) communicated | Show ran but no workload impact warning | No confirmation at all |
| Idempotency | Second delete returns `ResourceNotFound` (idempotent) | Second attempt errors but safe | Second attempt causes cascade on related resources |
| Traceability | Full trace: show + confirm + delete + verify | Delete only, no show | No trace |

### Stop AKS Cluster
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Cluster transitions to `Stopped` state; `az aks show` confirms | Confirmed stopped but timing | Not stopped or wrong cluster |
| Safety | User warned about workload downtime; explicit confirmation | Warning issued but confirmation unclear | No warning about workload impact |
| Idempotency | Second stop is no-op | Second stop errors | N/A |
| Traceability | Full command + state check before/after | State not verified after | No trace |

### Scale Node Pool (including to 0)
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Node pool scaled to requested count; `az aks nodepool show` confirms | Scaled but not to exact count | Wrong pool scaled or error |
| Safety | **Scale-to-0**: explicit confirmation + workload eviction warning issued. **Scale-up**: standard confirm | Scale-down without full warning | Scale-to-0 without any confirmation |
| Idempotency | Re-scaling to same count no-op | N/A | N/A |
| Traceability | Full trace: current count → confirm → scale → verify | Verify skipped | No trace |

### Upgrade Cluster
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Cluster upgraded to target version; `az aks show` confirms `kubernetesVersion` | Upgraded but some node pools not rolled | Wrong version applied or failed |
| Safety | Available upgrades checked first (`az aks get-upgrades`); user confirmed version; rollback strategy documented | Upgrades checked but no rollback plan | No pre-upgrade check |
| Idempotency | Re-upgrade to same version no-op | N/A | Re-upgrade causes node drain + re-create |
| Traceability | Full trace: get-upgrades → confirm → upgrade → verify | No pre-upgrade check | No trace |

### Node Pool Operations (add / delete)
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Node pool added/deleted as requested; `nodepool show` or list confirms | Added but wrong VM size | Wrong pool or error unhandled |
| Safety | Delete pool: confirm + pod disruption warning. Add pool: standard confirm | Delete warned but no disruption details | Delete pool without any confirmation |
| Idempotency | Add same pool again errors as duplicate (safe); delete already-deleted pool returns not-found | N/A | Delete causes cascade to workloads |
| Traceability | Full trace: list → confirm → execute → verify | Verify skipped | No trace |

### kubectl / Credential Operations (get-credentials)
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Credentials fetched; `kubectl cluster-info` succeeds | Credentials fetched but not verified | Credentials failed or wrong cluster |
| Safety | No credential leak; kubeconfig merged appropriately | N/A | Credential printed to stdout |
| Idempotency | Multiple get-credentials safe (merge mode) | N/A | N/A |
| Traceability | Command + verification captured | Verification skipped | No trace |

## Checklist (Critic Must Verify)

Before scoring, the Critic MUST verify:

- [ ] **Variables resolved**: no raw `{{env.*}}` / `{{user.*}}` in executed commands
- [ ] **RG present**: every `az aks` command includes `--resource-group`
- [ ] **Location valid**: uses Azure naming (e.g. `eastus`)
- [ ] **Delete confirmation**: `az aks show` ran before `az aks delete`; user typed exact cluster name; workload impact communicated
- [ ] **Stop confirmation**: user warned about downtime; explicit approval obtained
- [ ] **Upgrade pre-check**: `az aks get-upgrades` executed before `az aks upgrade`
- [ ] **Scale-to-0 gate**: explicit confirmation + pod eviction warning for node count = 0
- [ ] **JSON output**: `--output json` on every CLI command
- [ ] **Error handling**: recovery table consulted; HALT vs retry decision recorded
- [ ] **No credential leak**: output does not contain `AZURE_CLIENT_SECRET`, kubeconfig data, or SSH keys
- [ ] **Identity model**: `--enable-managed-identity` used (not deprecated `--service-principal`)