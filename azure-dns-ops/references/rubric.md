# Rubric — azure-dns-ops

> GCL rubric for Azure DNS operations. See `AGENTS.md §3` for dimension definitions and thresholds.

## Dimensions

| Dimension | Scale | Default threshold | Destructive threshold (zone delete / record set delete) |
|-----------|-------|-------------------|---------------------------------------------------------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Safety** | 0 / 1 | = 1 | = 1 |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |

**Safety = 0 → ABORT immediately.**

## Operation-Specific Scoring Guidance

### Create DNS Zone

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Zone created with correct name/RG; provisioningState `Succeeded`; NS records present | Created but wrong zone type (public vs private) | Wrong subscription or RG |
| Safety | Pre-flight: zone name format, availability, and RG checked | Pre-flight partially done | No pre-flight checks |
| Idempotency | Re-run detects existing zone and reports `ZoneAlreadyExists` (safe) | N/A | N/A |
| Traceability | Full command + `az network dns zone show` verify | Partial capture | No trace saved |
| Spec Compliance | Uses `az network dns zone` commands with `--output json`; SDK fallback documented | Minor omission | Hallucinated flag or missing RG |

### Delete DNS Zone

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Zone deleted; `az network dns zone show` returns `ResourceNotFound` | Wrong zone shown first | Wrong zone deleted |
| Safety | Show record sets and NS records first; warn about delegation loss ("All DNS resolution for [zone] will stop"); exact-name confirmation | Show ran but no delegation impact warning | No confirmation at all |
| Idempotency | Second delete returns `ResourceNotFound` (idempotent) | Second attempt errors but safe | N/A |
| Traceability | Full trace: list-records → confirm → delete → verify | Delete only, no list | No trace |

### Create / Update Record Set

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Record set created/updated with correct type, TTL, values; verify via `record-set show` | TTL or metadata mismatch | Wrong name, type, or values applied |
| Safety | CNAME apex conflict checked; TTL and record values validated | Partial validation | No validation of CNAME conflict |
| Idempotency | Re-run with same params safe (update idempotent) | N/A | Duplicate records created |
| Traceability | Full command + `record-set show` verify | Verify skipped | No trace |

### Delete Record Set

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Record set deleted; `record-set show` returns `ResourceNotFound` | Wrong record shown first | Wrong record deleted |
| Safety | Show current record values; warn about resolution impact; exact-name+type confirmation | Warning present but incomplete | No confirmation |
| Idempotency | Second delete returns `ResourceNotFound` (idempotent) | N/A | N/A |
| Traceability | Full trace: show → confirm → delete → verify | Verify skipped | No trace |

### Import / Export Zone File

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Import: all records from file created; Export: file contains all current records | Partial import/export | Wrong file or failed operation |
| Safety | Import: review file for overwrites before execution; Export: confirm file path | File not reviewed | Imported without review |
| Idempotency | Re-import same file safe (update idempotent) | N/A | Re-import creates duplicates |
| Traceability | Full trace: file review → import/export → verify | Verify skipped | No trace |

## Checklist (Critic Must Verify)

- [ ] Variables resolved; no raw `{{env.*}}` / `{{user.*}}` in executed commands
- [ ] Every `az network dns` command includes `--resource-group` where required
- [ ] Correct command family: `az network dns` for public, `az network private-dns` for private
- [ ] `--output json` used on CLI commands except explicit `-o tsv` queries
- [ ] Zone name format valid (no trailing dot in `--name` parameter)
- [ ] Zone create: availability and format checked before creation
- [ ] Zone delete: record set list shown; delegation impact communicated ("All DNS resolution for [zone] will stop"); exact name confirmation
- [ ] Record set create/update: CNAME apex conflict checked; TTL validated
- [ ] Record set delete: current values shown; resolution impact warning; exact name+type confirmation
- [ ] Import: file reviewed for overwrites before execution
- [ ] Recovery table consulted; HALT vs retry recorded
- [ ] No credential leak: `AZURE_CLIENT_SECRET`, tokens, or connection strings absent from trace
