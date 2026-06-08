# Rubric — azure-appservice-ops

> GCL rubric for Azure App Service operations. See `AGENTS.md §3` for dimension definitions and thresholds.

## Dimensions

| Dimension | Scale | Default threshold | Destructive / production-impact threshold |
|-----------|-------|-------------------|-------------------------------------------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Safety** | 0 / 1 | = 1 | = 1 |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |

**Safety = 0 → ABORT immediately.**

## Operation-Specific Scoring Guidance

### Create Plan / Web App

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Plan and app created with correct Resource Group, Location, SKU, runtime, and state | Created but runtime/SKU detail mismatched | Wrong subscription, plan, app, or Resource Group |
| Safety | Resource Group, Location, name availability, SKU, and runtime checked | Some pre-flight checks skipped | No pre-flight checks |
| Idempotency | Re-run detects existing plan/app and avoids duplicate side-effects | Needs manual interpretation | Creates unintended second app/plan |
| Traceability | Command, args, stdout, stderr, exit code, and validation captured | Partial trace | No trace |
| Spec Compliance | Uses `az appservice`/`az webapp` with JSON output; SDK fallback documented | Minor omission | Hallucinated flag or missing Resource Group |

### Stop / Restart / Scale Down / SKU Downgrade

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Target app/plan changed to intended state and verified | Operation accepted but not verified | Wrong app/plan mutated |
| Safety | Production availability/capacity impact communicated and exact-name confirmation obtained | Warning present but no exact confirmation | Mutation executed without warning |
| Idempotency | Re-run results in same state | N/A | Re-run causes extra disruption |
| Traceability | Before/after state and command trace captured | Partial trace | No trace |

### Slot Swap

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Source and target slots swapped as intended; hostname/routing verified | Swap accepted but routing not verified | Wrong slot swapped |
| Safety | Source/target shown; production impact warning; exact confirmation | Warning but incomplete slot context | Swap without confirmation |
| Idempotency | Repeated swap behavior understood and confirmed | N/A | Accidental rollback/swap loop |
| Traceability | Slot list, command, and verify trace captured | Partial trace | No trace |

### Delete Web App / App Service Plan

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Target deleted; show returns `ResourceNotFound` | Delete accepted but not verified | Wrong app/plan deleted |
| Safety | Show app/plan details; for plan delete list attached apps; traffic/data impact warning; exact-name confirmation | Warning present but attached apps not listed | No confirmation or dependencies ignored |
| Idempotency | Second delete safe `ResourceNotFound` | N/A | Cascading plan delete surprises user |
| Traceability | Full trace: show/list → confirm → delete → verify | Delete and verify only | No trace |

### App Settings / Connection Strings

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Intended keys updated and app config verified | Some keys updated | Wrong keys or app mutated |
| Safety | Secret-like values masked in trace; source of secrets is `{{env.*}}` | Key names shown but masking evidence incomplete | Secret values leaked |
| Idempotency | Re-run sets same values without drift | N/A | Re-run appends/duplicates settings |
| Traceability | Key names and masked value state captured | Partial trace | No trace |

## Checklist (Critic Must Verify)

- [ ] Variables resolved; no raw `{{env.*}}` / `{{user.*}}` in executed commands
- [ ] Every CLI command includes `--resource-group` where required
- [ ] Azure term **Location** used and validated
- [ ] `--output json` used on CLI commands except log streaming or scalar extraction
- [ ] Web App name uniqueness checked before create
- [ ] SKU supports requested features such as slots, VNet integration, or scale
- [ ] Stop/restart/scale/slot swap includes availability impact warning and confirmation
- [ ] Plan delete lists attached apps before confirmation
- [ ] App settings traces mask secret-like values
- [ ] Recovery table consulted; HALT vs retry recorded
- [ ] No credential leak: publishing profiles, connection strings, tokens, or `AZURE_CLIENT_SECRET` absent from trace
