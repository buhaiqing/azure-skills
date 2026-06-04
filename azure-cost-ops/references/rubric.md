# Rubric — azure-cost-ops

> GCL rubric for Azure Cost Management operations.
> See `AGENTS.md §3` for dimension definitions and thresholds.
> **GCL: recommended, max_iter=3. Most operations are read-only queries.**

## Dimensions

| Dimension | Scale | Default threshold | Budget delete / modification threshold |
|-----------|-------|-------------------|----------------------------------------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Safety** | 0 / 1 | = 1 | = 1 |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |

**Safety = 0 → ABORT immediately.**

## Operation-Specific Scoring Guidance

### Cost Query (read-only)
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Query returns cost data grouped by requested dimension for correct timeframe | Returns data but dimension/timeframe slightly off | Wrong query or empty result |
| Safety | Read-only; no mutation | N/A | N/A |
| Idempotency | Re-query returns same data | Time-bound differences expected | N/A |
| Traceability | Full query + row count + top-N entries captured | Partial capture | No trace |
| Spec Compliance | Valid scope, timeframe, grouping; correct `--type` | Minor scope/grouping issue | Invalid dimension name |

### Create Budget
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Budget created with correct amount/timeframe/notifications; `az consumption budget show` confirms | Created but notification email wrong | Not created or wrong amount |
| Safety | Budget amount and notification email confirmed with user; cost impact clear | Confirmation but email not verified | Created without confirmation |
| Idempotency | Re-create same budget idempotent (name conflict — safe) | N/A | N/A |
| Traceability | Full command + budget show verify | Verify skipped | No trace |
| Spec Compliance | Valid amount, timeframe, notification syntax | Minor format issue | Invalid threshold operator |

### Delete Budget
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Budget deleted; `az consumption budget show` returns not-found | Wrong budget shown first | Wrong budget deleted |
| Safety | `az consumption budget show` before delete; budget details displayed; exact name confirmation | Show ran but no details | No confirmation at all |
| Idempotency | Second delete returns not-found (safe) | N/A | N/A |
| Traceability | Full trace: show → confirm → delete → verify | Verify skipped | No trace |

### Invoice / Reservation (read-only)
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Correct invoice/reservation data returned | Data returned but incomplete | Wrong query or error |
| Safety | Read-only | N/A | N/A |
| Idempotency | Re-query returns same data | N/A | N/A |
| Traceability | Command + result captured | Partial capture | No trace |

## Checklist (Critic Must Verify)

- [ ] **Scope valid**: `/subscriptions/{id}` or more specific scope path
- [ ] **Timeframe valid**: MonthToDate / TheLastMonth / Custom with YYYY-MM-DD
- [ ] **Cost type correct**: ActualCost (real) vs AmortizedCost (with RIs)
- [ ] **Budget delete**: `az consumption budget show` before delete; exact name confirmation
- [ ] **Budget create**: amount + email confirmed with user
- [ ] **Provider registered**: `Microsoft.CostManagement` must be registered
- [ ] **JSON output**: `--output json` on every CLI command
- [ ] **No credential leak**: billing account IDs not exposed unnecessarily
- [ ] **Variables resolved**: no raw `{{env.*}}` or `{{user.*}}` in executed commands