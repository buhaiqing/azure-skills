# Rubric — azure-vm-ops

> GCL rubric for Azure Virtual Machine operations.
> See `AGENTS.md §3` for dimension definitions and thresholds.

## Dimensions

| Dimension | Scale | Default threshold | Destructive threshold (delete/stop/deallocate) |
|-----------|-------|-------------------|------------------------------------------------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Safety** | 0 / 1 | = 1 | = 1 |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |

**Safety = 0 → ABORT immediately.**

## Operation-Specific Scoring Guidance

### Create VM
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | VM created in correct RG/location/size/image; provisioning state = Succeeded | VM created but size/image mismatch | VM not created or wrong subscription |
| Safety | Pre-flight checks all passed | Minor pre-flight skipped | Destructive side-effect (e.g. overwriting existing) |
| Idempotency | `--output json` parseable; retry with same params idempotent | Retry creates duplicate NIC/IP | Retry causes duplicate resources |
| Traceability | Full command + stdout + stderr captured | Partial capture | No trace saved |
| Spec Compliance | Follows `core-concepts.md` and `azure-cli-conventions.md` | Minor deviation | Hallucinated flag or missing RG |

### Delete VM
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | VM deleted; exact name matches; confirmation obtained | Wrong VM shown first | Wrong VM deleted |
| Safety | Explicit human confirmation exact VM name; `az vm show` shown before delete | Confirmation prompt but no `az vm show` | No confirmation at all |
| Idempotency | Second delete returns `ResourceNotFound` (idempotent) | Second attempt errors but safe | Second attempt causes cascade delete |
| Traceability | Full trace including show + confirm + delete | Delete only, no show | No trace |

### Stop / Deallocate VM
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | VM transitions to `Stopped (deallocated)` / `Stopped` | Wrong VM stopped | VM not stopped; error unhandled |
| Safety | Confirmation obtained; `--skip-deallocation` clarified | Skip-deallocation unclear | Stopped wrong VM |
| Idempotency | Second stop is no-op | Second stop errors | Second stop re-provisions |
| Traceability | Full command + power state check | Power state not verified | No trace |

### Start / Restart VM
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | VM transitions to Running | VM starts but takes long | VM fails to start; error ignored |
| Safety | No destructive side-effect checked | N/A | N/A (read-safe) |
| Idempotency | Multiple start calls safe | N/A | N/A |
| Traceability | Full command + power state verified | Power state not checked | No trace |

### Resize VM
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | VM size changed to requested; `az vm show` confirms | Size changed but VM must be restarted | Wrong size applied |
| Safety | User confirmed; VM state checked before resize | No VM state check | Resized while running without warning |
| Idempotency | Resize to same size no-op | N/A | N/A |
| Traceability | Full trace: check-skus → show → confirm → resize → verify | Missing SKU check | No trace |

### RunCommand / VM Extension
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Command executed with exit 0; output returned | Command ran with non-zero exit | Command not executed |
| Safety | Script content is non-malicious | Script not reviewed | Destructive script (rm -rf, etc.) |
| Idempotency | Re-running same script idempotent | Re-run causes duplicate state | Re-run causes infinite side-effect |
| Traceability | Command + output + exit code captured | Output only | No trace |

## Checklist (Critic Must Verify)

Before scoring, the Critic MUST confirm:

- [ ] **Variables resolved**: all `{{env.*}}`, `{{user.*}}` are populated (no raw placeholders in executed commands)
- [ ] **RG present**: every `az vm` command includes `--resource-group`
- [ ] **Location valid**: `{{user.location}}` uses Azure naming (e.g. `eastus`, not `east us` or `region=US East`)
- [ ] **Delete confirmation**: `az vm show` ran before `az vm delete`; user typed exact VM name
- [ ] **Stop clarification**: `--skip-deallocation` explicitly confirmed with user
- [ ] **JSON output**: `--output json` flag present in every CLI command
- [ ] **Error handling**: recovery table consulted; HALT vs retry decision recorded in trace
- [ ] **No credential leak**: output does not contain `AZURE_CLIENT_SECRET`, password, or SSH private key