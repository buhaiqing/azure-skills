# Rubric — azure-aci-ops

> GCL rubric for Azure Container Instances operations.
> See `AGENTS.md §3` for dimension definitions and thresholds.

## Dimensions

| Dimension | Scale | Default threshold | Destructive threshold (delete) |
|-----------|-------|-------------------|-------------------------------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Safety** | 0 / 1 | = 1 | = 1 |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |

**Safety = 0 → ABORT immediately.**

## Operation-Specific Scoring Guidance

### Create container group
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Created in correct RG/location/image; provisioningState = Succeeded | Created but wrong cpu/memory/restartPolicy | Not created / wrong subscription |
| Safety | Pre-flight passed; no destructive side-effect | Minor pre-flight skipped | Overwrote existing group unexpectedly |
| Idempotency | `begin_create_or_update` idempotent for same name | Duplicate IP/DNS label | Duplicate resource created |
| Traceability | Full command + stdout/stderr captured | Partial | No trace |
| Spec Compliance | Follows `core-concepts.md` (RG required, location format, JSON output) | Minor deviation | Hallucinated flag / missing RG |

### Delete container group
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Exact group deleted; confirmation obtained | Wrong group shown first | Wrong group deleted |
| Safety | `az container show` before delete; user typed exact name | Confirm prompt but no show | No confirmation at all |
| Idempotency | Second delete → ResourceNotFound (safe) | Second attempt errors but safe | Cascade/duplicate delete |
| Traceability | show + confirm + delete trace | delete only | No trace |

### Restart / Start（LRO，异步）
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Group transitions to Running as requested; LRO completes | State change slow (LRO still pending) | State change failed, unhandled |
| Safety | No destructive side-effect (restart/start is safe) | N/A | N/A |
| Idempotency | Repeated calls safe; LRO handles duplicate starts | N/A | N/A |
| Traceability | Command + state verified after LRO completion | State not verified | No trace |

### Stop（同步操作）
Stop 是同步操作（`client.container_groups.stop()`），非 LRO，无等待逻辑。已 stop 的容器组再次 stop 安全（幂等）。

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Group transitions to Stopped; sync call returns | State change slow | State change failed, unhandled |
| Safety | No destructive side-effect; stop does not delete | N/A | N/A |
| Idempotency | Already-stopped group stopped again → no-op, safe | N/A | N/A |
| Traceability | Command + state verified after call | State not verified | No trace |

### Stream logs
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Logs returned for correct container | Partial log | Wrong container / no output |
| Safety | Read-only, no mutation | N/A | N/A |
| Traceability | Command + output captured | Output only | No trace |

## Checklist (Critic Must Verify)

- [ ] **Variables resolved**: no raw `{{env.*}}`/`{{user.*}}` in executed commands
- [ ] **RG present**: every `az container` command includes `--resource-group`
- [ ] **Location valid**: `{{user.location}}` uses Azure naming (e.g. `eastus`)
- [ ] **Delete confirmation**: `az container show` ran before `az container delete`; user typed exact name
- [ ] **JSON output**: `--output json` present on every CLI command
- [ ] **SDK fidelity**: logs via `client.containers.list_logs`, not `container_groups.list_logs`
- [ ] **Error handling**: recovery matrix consulted; HALT vs retry recorded
- [ ] **No credential leak**: no `AZURE_CLIENT_SECRET`, registry password, or SSH key in output
