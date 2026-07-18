---
name: azure-audit-ops
description: >-
  Use when auditing Azure resources, reviewing activity logs, checking RBAC/IAM
  assignments, inspecting resource locks, evaluating diagnostic settings completeness,
  assessing policy compliance, or performing security posture reviews. Cross-product
  read-only audit skill. User mentions "audit", "review", "inspect", "compliance",
  "security check", "activity log", "who did what", "lock", "policy", "RBAC".
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal
  with Reader role or higher), network access to Azure endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Audit Operations Skill

## Overview

**Cross-product read-only audit skill**. Inspects Azure resources for security, compliance,
configuration completeness, and operational hygiene. It does NOT mutate resources. Remediation
findings are delegated to the appropriate service skill (e.g. `azure-monitor-ops` for diagnostic
settings, `azure-blobstorage-ops` for public access).

## Trigger & Scope

### SHOULD Use When
- User mentions "audit", "review", "inspect", "who did what", "what changed"
- Task involves: Activity Log query, RBAC/IAM review, resource lock check, diagnostic settings review
- Keywords: audit, activity log, operation log, change tracking, role assignment, RBAC, IAM, policy, compliance, lock, canarydelete, security review, nsg review, public endpoint, firewall rule
- Pre-migration or pre-deployment compliance check
- Periodic security hygiene review

### SHOULD NOT Use When
- Creating/modifying/deleting resources → delegate to specific service skill
- Billing/cost analysis → delegate to: `azure-cost-ops`
- Real-time monitoring/alerts → delegate to: `azure-monitor-ops`
- Single resource diagnostics → delegate to: specific service skill's troubleshooting

## Variable Convention

Auth quad `{{env.AZURE_SUBSCRIPTION_ID/TENANT_ID/CLIENT_ID/SECRET}}` — NEVER ask user, fail if unset —
see [azure-cli-conventions.md](../../azure-skill-generator/references/azure-cli-conventions.md#credential-sources-priority-order).
Business placeholders:

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{user.resource_group}}` | User input | Ask once; reuse; optional for subscription-level audit |
| `{{user.target_resource_id}}` | User input | Specific resource to audit |
| `{{user.time_range}}` | User input | Time range for activity log (e.g. "7d", "2026-05-01T00:00:00Z/2026-06-01T00:00:00Z") |
| `{{output.activity_log_entries}}` | Last API response | Parsed activity log entries |
| `{{output.audit_report}}` | Last API response | Structured audit findings |

## Execution Flow Pattern

Every audit follows: **Scope → Collect → Analyze → Report**.

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Scope  │ → │ Collect  │ → │ Analyze  │ → │  Report  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

Pre-flight (CLI/credentials/subscription checks) and the 3× retry fallback are standardized —
see [azure-cli-conventions.md](../../azure-skill-generator/references/azure-cli-conventions.md)
(Pre-flight + Retry Strategy). Full `az` command blocks and SDK fallback are in
[integration.md](references/integration.md).

## Operations

Each operation below shows the primary CLI entry point. Full command variants, filters, and the
Azure SDK for Python fallback are in [integration.md](references/integration.md).

### 1. Activity Log Review (Who did what)
`az monitor activity-log list --start-time "{{user.time_range_start}}" --end-time "{{user.time_range_end}}" --output json`
Filter by `--caller`, `--operation`, `--resource-group`, `--severity`. Full variants → integration.md.

### 2. RBAC / Role Assignment Audit
`az role assignment list --output json`
Add `--assignee`, `--resource-group`, or `--include-inherited` to scope. Custom roles: `az role definition list --custom-role-only true`.

### 3. Resource Lock Audit
`az lock list --output json`
Add `--resource-group` or `--resource "{{user.target_resource_id}}"`. Find critical resources missing `CanNotDelete`/`ReadOnly` locks.

### 4. Diagnostic Settings Completeness
`az monitor diagnostic-settings list --resource "{{user.target_resource_id}}" --output json`
Flag resources with no diagnostic settings (monitoring gap).

### 5. Policy Compliance
`az policy state list --output json`
Filter `--filter "complianceState eq 'NonCompliant'"`. Assignments: `az policy assignment list`.

### 6. Security Posture Review
`az network nsg list --query "[].{Name:name, Rules:securityRules[?access=='Allow' && sourceAddressPrefix=='*']}" --output json`
Also audit storage public access, VM public IPs, AKS RBAC-disabled, SQL firewall `0.0.0.0`, Key Vault soft-delete. Full queries → integration.md.

### 7. Resource Inventory & Configuration Drift
`az resource list --output json`
Tag/RG drift: `--query "[?tags==null || !tags.Environment]"`. Full queries → integration.md.

## Safety & RBAC Notes (mandatory)

- **This skill is strictly read-only.** No `create`/`update`/`delete` is issued by this skill.
- **RBAC is sensitive**: role-assignment findings (Owner/Contributor at subscription scope, orphaned
  SPs, wildcard custom roles) must be reported, NOT auto-remediated. Any remediation (e.g.
  `az role assignment delete`) requires an explicit human-confirmation gate and must be delegated to
  the owning service skill or performed only after the user confirms in writing.
- **Locks**: reporting missing locks is safe; creating a lock (`az lock create`) is a mutation and
  requires confirmation — delegate or confirm first.
- **Credential masking**: never print `{{env.AZURE_CLIENT_SECRET}}` in any output or trace; mask as `***`.

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate.
See `AGENTS.md §3–§8` for the spec.

| Parameter | Value |
|-----------|-------|
| GCL | **optional** (read-only audit — GCL recommended but not required) |
| max_iterations | 3 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### Note

This skill is **read-only**. All audit operations are safe to retry. The main GCL concern is
**data completeness** (did the query actually cover the full scope?) and **report accuracy**
(are findings correctly classified?). GCL is recommended for comprehensive audits (multi-service
sweeps) but may be skipped for quick single-resource lookups.

## Reference Files

- [Core Concepts](references/core-concepts.md) — categories, RBAC/lock/policy concepts, report template, delegation
- [Troubleshooting](references/troubleshooting.md) — permissions, throttling, empty results
- [Integration Setup](references/integration.md) — Reader role setup, full `az` command blocks, SDK fallback
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)


