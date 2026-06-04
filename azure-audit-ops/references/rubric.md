# Rubric — azure-audit-ops

> GCL rubric for Azure audit operations.
> See `AGENTS.md §3` for dimension definitions and thresholds.
> **GCL: optional, max_iter=3.** Read-only audit — GCL recommended for comprehensive multi-service sweeps.

## Dimensions

| Dimension | Scale | Default threshold | Notes |
|-----------|-------|-------------------|-------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | Query returned correct data; findings accurate |
| **Safety** | 0 / 1 | = 1 | Read-only — no mutations; no credential leak |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | Re-querying returns consistent results |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | Queries + results captured in structured report |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | Correct CLI commands; valid filters; proper delegation |

## Operation-Specific Scoring Guidance

### Activity Log Query
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Query returns expected entries matching time range + caller + operation | Returns data but time range/scope too broad | Wrong query or no data |
| Safety | Read-only; no mutation | N/A | Credential leak in output |
| Idempotency | Re-query returns same entries | Time-sensitive entries differ (normal) | N/A |
| Traceability | Query + result count + key entries captured | Partial capture | No trace |
| Spec Compliance | Valid time format; correct filter; proper `--query` syntax | Minor format issue | Invalid KQL or hallucinated field |

### RBAC Audit
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | All role assignments at requested scope returned; privileged roles identified | Returned but missing inherited assignments | Wrong scope queried |
| Safety | Read-only | N/A | N/A |
| Idempotency | Re-query returns same assignments | N/A | N/A |
| Traceability | Scope + filters + results + findings captured | Scope not recorded | No trace |
| Spec Compliance | `az role assignment` correct; `--include-inherited` used appropriately | Missing `--include-inherited` when needed | Wrong command alias |

### Resource Lock Audit
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | All locks at requested scope returned; resources without locks identified | Returned but didn't cross-check with resource inventory | Wrong scope |
| Safety | Read-only | N/A | N/A |
| Idempotency | Re-query returns same locks | N/A | N/A |
| Traceability | Scope + locks + gap analysis captured | Gap analysis not done | No trace |
| Spec Compliance | `az lock list` with correct scope | Minor scope ambiguity | Wrong lock command |

### Policy Compliance Audit
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Non-compliant resources identified; policy assignment names returned | Count returned but no resource list | Wrong filter |
| Safety | Read-only | N/A | N/A |
| Idempotency | Re-query returns same compliance state (or updated — policy evaluation is async) | N/A | N/A |
| Traceability | Compliance summary + non-compliant list captured | Summary only | No trace |
| Spec Compliance | `az policy state list` with correct filter | Missing severity classification | Wrong command |

### Security Posture Check
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Find all resources with security misconfiguration (public access, broad NSG, etc.) | Found some but missed others | Wrong query or false negatives |
| Safety | Read-only | N/A | N/A |
| Idempotency | Re-running produces same findings | N/A | N/A |
| Traceability | Resource list + risk summary captured | Resources not listed | No trace |
| Spec Compliance | Correct `--query` filters; hallucinated property names = 0 | Minor filter imprecision | Completely wrong filter |

### Report Generation
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Structured report with Category, Finding, Severity, Resource, Recommendation | Report generated but missing columns | No report |
| Safety | No credential leak in report | N/A | Secrets in report output |
| Idempotency | Re-running audit produces consistent report | N/A | N/A |
| Traceability | Report saved as structured output | Ad-hoc summary | Not saved |
| Spec Compliance | Follows the report template in SKILL.md | Minor format deviation | Different format entirely |

## Checklist (Critic Must Verify)

- [ ] **Read-only confirmed**: no `create`, `delete`, `update`, `set`, `start`, `stop`, `restart` operations in trace
- [ ] **Time range valid**: ISO 8601 format for activity log queries
- [ ] **Scope correct**: subscription-level vs resource-group-level verified
- [ ] **Filters accurate**: `--query` syntax valid; property names match Azure REST API
- [ ] **Delegation correct**: findings requiring remediation delegated to proper skill (not inlined)
- [ ] **Report structured**: contains Category, Finding, Severity, Resource, Recommendation
- [ ] **JSON output**: `--output json` on every CLI command
- [ ] **No credential leak**: `AZURE_CLIENT_SECRET`, passwords, keys not in output
- [ ] **Variables resolved**: no raw `{{env.*}}` or `{{user.*}}` in executed commands