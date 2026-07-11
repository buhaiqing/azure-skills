# Rubric — azure-backup-ops

> GCL rubric for Azure Backup / Recovery Services operations.
> See `AGENTS.md §3` for dimension definitions and thresholds.

## Dimensions

| Dimension | Scale | Default threshold | Destructive threshold (stop-protection/delete-backup-data) |
|-----------|-------|-------------------|------------------------------------------------------------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Safety** | 0 / 1 | = 1 | = 1 |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |

**Safety = 0 → ABORT immediately.**

## Operation-Specific Scoring Guidance

### Create Vault
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Vault created in correct RG/location; provisioning state = Succeeded | Vault created but wrong location or SKU | Vault not created or wrong subscription |
| Safety | Pre-flight checks all passed | Minor pre-flight skipped | Destructive side-effect (overwriting existing vault) |
| Idempotency | Retry with same params idempotent (name unique per RG) | Retry fails with conflict | Retry creates duplicate vault |
| Traceability | Full command + stdout + stderr captured | Partial capture | No trace saved |
| Spec Compliance | Follows `core-concepts.md` and `azure-cli-conventions.md` | Minor deviation | Hallucinated flag or missing RG |

### Stop Protection / Delete Backup Data
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Correct item stopped/deleted; exact name matches; confirmation obtained | Wrong item shown first | Wrong item stopped or data deleted |
| Safety | Explicit human confirmation: exact vault + item name; `az backup item show` before disable | Confirmation prompt but no show command | No confirmation at all |
| Idempotency | Second disable returns error (already stopped) — safe | Second disable errors but no data loss | Second disable causes cascade deletion |
| Traceability | Full trace: show → confirm → disable → verify | Disable only, no show | No trace |

### Restore
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Restore initiated to correct target; recovery point verified | Restore started but wrong target | Wrong recovery point restored |
| Safety | Recovery point consistency verified; target confirmed | Target not fully verified | Restore to wrong subscription |
| Idempotency | Restore to same target fails (file exists) | N/A | N/A |
| Traceability | Full trace: list RP → show RP → confirm → restore → verify | Missing RP verification | No trace |

### Configure Backup / Update Policy
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Backup configured with correct policy on correct item | Wrong policy applied | Item not found; error unhandled |
| Safety | Item eligibility verified; policy retention reviewed | Retention not checked | Backup configured on wrong item |
| Idempotency | Re-applying same config is no-op | Re-apply causes duplicate schedule | Re-apply creates conflicting policy |
| Traceability | Full trace: policy show → item show → enable → verify | Missing policy verification | No trace |

### Show / List
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Correct resource state returned; fields verified | Data returned but incomplete | Wrong resource queried |
| Safety | Read-only; no side-effect | N/A | N/A |
| Idempotency | Multiple calls produce same result | N/A | N/A |
| Traceability | Command + output captured | Partial capture | No trace |

## Checklist (Critic Must Verify)

Before scoring, the Critic MUST confirm:

- [ ] **Variables resolved**: all `{{env.*}}`, `{{user.*}}` are populated (no raw placeholders in executed commands)
- [ ] **RG present**: every `az backup` command includes `--resource-group`
- [ ] **Vault name valid**: matches Recovery Services naming rules (2-50 chars, alphanumeric + hyphens)
- [ ] **Stop-protection confirmation**: `az backup item show` ran before `az backup protection disable`; user typed exact vault + item name
- [ ] **Restore verification**: recovery point checked for consistency before restore
- [ ] **JSON output**: `--output json` flag present in every CLI command
- [ ] **Error handling**: recovery table consulted; HALT vs retry decision recorded in trace
- [ ] **No credential leak**: output does not contain `AZURE_CLIENT_SECRET` or other secrets
- [ ] **Soft-delete awareness**: stop-protection with `--delete-backup-data` considered against soft-delete state
