# Rubric — azure-monitor-ops

> GCL rubric for Azure Monitor operations.
> See `AGENTS.md §3` for dimension definitions and thresholds.
> **GCL: recommended, max_iter=3** (most operations are read-only or advisory).

## Dimensions

| Dimension | Scale | Default threshold | Destructive threshold (alert rule delete / action group delete / diagnostic setting delete) |
|-----------|-------|-------------------|----------------------------------------------------------------------------------------------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Safety** | 0 / 1 | = 1 | = 1 |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |

**Safety = 0 → ABORT immediately.**

> For read-only operations (list, show, query), GCL is optional. The Critic may skip but the
> trace is still recorded. For **delete** operations (alert rule, action group, diagnostic setting),
> GCL is required with Safety=1 gate.

## Operation-Specific Scoring Guidance

### Query Metrics / Activity Log / Log Analytics (read-only)
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Query returned correct data for the time range/resource | Query returned but incomplete | Wrong query or no data |
| Safety | Read-only; no safety risk | N/A | N/A |
| Idempotency | Re-query returns same data (idempotent) | N/A | Mutation side-effect (impossible for read-only) |
| Traceability | Full query + result excerpt captured | Partial capture | No trace |
| Spec Compliance | Valid KQL syntax; correct resource URI; JSON output | Minor format issue | Invalid KQL or hallucinated metric name |

### Create Alert Rule
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Alert rule created with correct condition/action/window; provisioning = Succeeded | Created but condition slightly off | Not created or wrong resource scope |
| Safety | Action group verified to exist; severity and description set | Action group not verified | No action group attached (silent alert) |
| Idempotency | Re-create same rule idempotent (name conflict — safe) | N/A | Duplicate rules cause duplicate notifications |
| Traceability | Full command + `az monitor metrics alert show` verify | Verify skipped | No trace |

### Delete Alert Rule
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Alert rule deleted; `az monitor metrics alert show` returns not-found | Wrong rule shown first | Wrong rule deleted |
| Safety | Confirmation; `az monitor metrics alert show` before delete; **monitoring gap** warning ("No alerts will fire for this condition") | Show ran but no gap warning | No confirmation at all |
| Idempotency | Second delete returns not-found (safe) | N/A | N/A |
| Traceability | Full trace: show → confirm → delete → verify | Verify skipped | No trace |

### Delete Action Group
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Action group deleted; `action-group show` returns not-found | Wrong group shown first | Wrong group deleted |
| Safety | Check if action group is referenced by any alert rule; if so, **list affected rules** and warn; confirm | Warned but affected rules not listed | Deleted while in use by active rules |
| Idempotency | Second delete returns not-found (safe) | N/A | N/A |
| Traceability | Full trace: show → check-references → confirm → delete → verify | Rule reference check skipped | No trace |

### Create / Delete Diagnostic Setting
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Diagnostic setting created/deleted; `diagnostic-settings show` confirms | Created but log/metric categories mismatch | Wrong setting or error |
| Safety | **Delete**: warning ("Logs and metrics will stop flowing to workspace/event hub"); confirm | Warning but not specific | Deleted without warning |
| Idempotency | Re-create same setting idempotent (overwrites) | N/A | N/A |
| Traceability | Full trace: show → confirm → execute → verify | Verify skipped | No trace |

### Create Action Group
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Action group created with correct email/webhook/ARM actions; `action-group show` confirms | Created but wrong email | Not created |
| Safety | Email/webhook URLs validated for format | URL not validated | Sensitive webhook URL exposed in trace |
| Idempotency | Re-create same action group idempotent (name conflict — safe) | N/A | N/A |
| Traceability | Full command + verify | Verify skipped | No trace |

## Checklist (Critic Must Verify)

Before scoring, the Critic MUST verify:

- [ ] **Variables resolved**: no raw `{{env.*}}` / `{{user.*}}` in executed commands
- [ ] **Read vs Write**: confirm operation is read-only (GCL optional) or write/delete (GCL required)
- [ ] **Alert rule delete**: `az monitor metrics alert show` before delete; monitoring gap communicated
- [ ] **Action group delete**: checked if referenced by any alert rule; affected rules listed
- [ ] **Diagnostic setting delete**: log/metric data flow gap communicated
- [ ] **Action group email/webhook URL**: not exposed in trace; format validated
- [ ] **JSON output**: `--output json` on every CLI command
- [ ] **Error handling**: recovery table consulted; HALT on ResourceNotFound
- [ ] **No credential leak**: webhook URLs, API keys not in output