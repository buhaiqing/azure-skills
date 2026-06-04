# Rubric — azure-skill-generator (Meta-Skill)

> GCL rubric for the meta-skill that scaffolds Azure operational skills.
> See `AGENTS.md §3` for dimension definitions and thresholds.
> **GCL: optional, max_iter=3.** Meta-skill generates markdown, not live cloud operations.

## Dimensions

| Dimension | Scale | Default threshold | Notes |
|-----------|-------|-------------------|-------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | Generated skill follows template exactly |
| **Safety** | 0 / 1 | = 1 | Generated skill includes safety gates for destructive ops |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | Re-running generator produces same output |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | Source references (docs, CLI help, SDK) captured |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | Follows template, variable convention, agentskills.io spec |

**Safety = 0 → ABORT immediately.** Generated skill without safety gates could cause production data loss.

## Operation-Specific Scoring Guidance

### Scaffold New Skill
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Full `azure-[service]-ops/` layout created matching template; frontmatter valid YAML; all required files present | Layout created but missing some `references/` files | Layout not created or wrong structure |
| Safety | Every destructive operation in generated skill has explicit human confirmation gate; `{{env.*}}` placeholders used (not real secrets) | Some destructive ops missing safety gate | No safety gates at all |
| Idempotency | Re-running generator produces identical output (safe to overwrite) | Minor drift on re-run | Re-run corrupts existing files |
| Traceability | Source of truth cited: Azure docs URL, `az [service] --help` output, SDK module name | Partial references | No source cited |
| Spec Compliance | Uses `azure-skill-template.md`; follows `{{env.*}}`/`{{user.*}}`/`{{output.*}}` convention; YAML frontmatter valid | Minor deviation | Template structure broken |

### Audit Existing Skill
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Skill correctly structured; all references exist; operations valid | Minor issues | Structural problems |
| Safety | All destructive ops have safety gates | Some missing | No gates |
| Idempotency | N/A (audit is read-only) | N/A | N/A |
| Traceability | Diff/status captured | Partial capture | No audit trail |
| Spec Compliance | Clean diff against template | Minor violations | Template violations found |

## Checklist (Critic Must Verify)

- [ ] **Template fidelity**: Generated files match `azure-skill-template.md` shape
- [ ] **Frontmatter valid**: YAML frontmatter parses; `name`, `description`, `version`, `metadata.*` all present
- [ ] **Safety gates**: Every destructive operation has `**Safety Gate**` heading + explicit confirmation step
- [ ] **Credentials**: `{{env.*}}` placeholders used; no real credentials or `{{user.*}}` for secrets
- [ ] **Dual-path**: Both Azure CLI and Azure SDK documented per operation
- [ ] **Variable convention**: `{{env.*}}` (secrets), `{{user.*}}` (input), `{{output.*}}` (API response)
- [ ] **Recovery table**: ≥ 4 error codes with HALT vs retry
- [ ] **SHOULD/SHOULD-NOT**: Clear trigger scope; delegation targets named
- [ ] **JSON output**: `--output json` in every CLI command
- [ ] **RG + Location**: Both params included in every resource operation
- [ ] **No credential leak**: generated skill does not contain real secrets; only `{{env.*}}` placeholders