---
name: azure-keyvault-ops
description: >-
  Use when operating or diagnosing Azure Key Vault. User mentions Key Vault,
  vault, secret, key, certificate, access policy, RBAC, managed identity 403,
  purge protection, soft-delete, certificate expiry, private endpoint, firewall,
  or Key Vault AIOps/RCA.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials,
  network access to Azure management endpoints and Key Vault data-plane endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-06-09"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure Key Vault Operations Skill

## Overview

Azure Key Vault protects secrets, keys, and certificates. This skill handles vault operations, safe object lifecycle diagnostics, RBAC/access-policy RCA, managed identity access troubleshooting, network/private endpoint analysis, certificate expiry review, and AIOps-assisted incident analysis. Keep this file concise; load references for commands, SDK patterns, RCA rules, and detailed scenarios.

## Trigger & Scope

### SHOULD Use When
- User mentions Key Vault, vault secret/key/certificate, access policy, RBAC mode, managed identity, `403 Forbidden`, purge protection, soft-delete, firewall, private endpoint, or certificate expiry.
- Task involves vault create/show/list/update/delete, secret/key/certificate list/show/set/delete/recover, access diagnostics, network diagnostics, or incident RCA.
- User asks for AIOps analysis, denied request spike, near-expiry certificate, unusual operation volume, delete/purge attempt, or private endpoint/firewall correlation.

### SHOULD NOT Use When
- Generic RBAC audit or Activity Log-only work → delegate to `azure-audit-ops`.
- Generic Monitor query/alert authoring → delegate to `azure-monitor-ops`.
- Billing/cost only → delegate to `azure-cost-ops`.
- Application code secret-loading changes → report evidence; app owners change code.
- HSM-specific cryptographic design beyond operational checks → escalate to security owner.

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; required for vault operations |
| `{{user.location}}` | User input | Azure Location, e.g. `eastus`; validate before create |
| `{{user.vault_name}}` | User input | Key Vault name |
| `{{user.secret_name}}` | User input | Secret name; never ask for secret value |
| `{{user.key_name}}` | User input | Key name |
| `{{user.certificate_name}}` | User input | Certificate name |
| `{{user.principal_id}}` | User input | Managed identity/service principal object ID |
| `{{user.analysis_window}}` | User input | Default `PT1H`; use `PT6H`/`P1D` for incidents |
| `{{output.vault_id}}` | CLI/SDK output | Parse from `.id` |
| `{{output.vault_uri}}` | CLI/SDK output | Parse from `.properties.vaultUri` |

## JSON Paths

```yaml
VAULT_ID: id
VAULT_URI: properties.vaultUri
TENANT_ID: properties.tenantId
RBAC_ENABLED: properties.enableRbacAuthorization
PURGE_PROTECTION: properties.enablePurgeProtection
SOFT_DELETE_RETENTION: properties.softDeleteRetentionInDays
PUBLIC_NETWORK_ACCESS: properties.publicNetworkAccess
PRIVATE_ENDPOINTS: properties.privateEndpointConnections[].privateEndpoint.id
```

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover → Report**.

| Phase | Required Actions |
|-------|------------------|
| Pre-flight | Verify CLI, credentials, subscription, Resource Group, Location, provider, RBAC/access model, network mode, and target object identity. |
| Execute | Use Azure CLI primary. Retry transient CLI failures up to 3x with backoff before SDK fallback. |
| Validate | Confirm vault/object state with `--output json`; poll LRO every 30s, max 30m unless reference says otherwise. |
| Recover | Apply HALT-vs-retry matrix; never print secret values or repeat destructive purge/delete blindly. |
| Report | Return evidence, confidence, safe next actions, security-owner review items, and actions requiring confirmation. |

## Operation Map

| Intent | Primary CLI | Reference |
|--------|-------------|-----------|
| Vault create/show/list/update/delete/recover/purge | `az keyvault` | [integration.md](references/integration.md) |
| Secret/key/certificate lifecycle | `az keyvault secret/key/certificate` | [integration.md](references/integration.md) |
| RBAC/access policy diagnostics | `az role assignment`, `az keyvault show` | [troubleshooting.md](references/troubleshooting.md) |
| Network/private endpoint/firewall diagnostics | `az keyvault network-rule`, private endpoint evidence | [troubleshooting.md](references/troubleshooting.md) |
| Certificate expiry and denied request analysis | Monitor logs, Activity Log, object metadata | [aiops.md](references/aiops.md) |

## Safety Gates

Require explicit human confirmation with exact vault name and Resource Group before:
- delete or purge vault, secret, key, or certificate;
- set/overwrite a secret, import/merge/delete a certificate, rotate/delete/disable a key;
- change RBAC assignments or access policies;
- disable or weaken purge protection/soft-delete posture where allowed;
- change public network access, firewall allowlists, trusted services, or private endpoint approval.

Never ask the user to paste secret values. If a secret value is required, instruct them to set it via their own secure local secret source.

## AIOps and RCA Rules

Use AIOps only for observation, correlation, diagnosis, and recommendations. Do not auto-remediate. Load [aiops.md](references/aiops.md) for denied request spikes, certificate near-expiry, unusual secret/key/cert operations, delete/purge attempts, private endpoint/firewall changes, or unknown access failures.

RCA output must include: symptom, timeline, object/access/network evidence, likely root causes, confidence, safe checks, approval-required actions, security-owner review items, and escalation criteria.

## Recovery Matrix

| Condition | Agent Action |
|-----------|--------------|
| AuthorizationFailed / Forbidden | HALT; identify RBAC vs access policy path from [troubleshooting.md](references/troubleshooting.md) |
| Vault/object not found | HALT; verify name, Resource Group, subscription, soft-delete state |
| PurgeProtection prevents purge | HALT; report protection state; do not bypass |
| Network denied / private DNS mismatch | HALT mutation; collect network evidence and escalate to network owner |
| Throttling / 429 | Backoff and retry up to 3x |
| 5xx / transient network | Retry up to 3x, then HALT with correlation ID |
| Destructive/security-sensitive action without confirmation | HALT; require explicit confirmation |

## Quality Gate

GCL is required for destructive/security-sensitive operations and recommended for incident RCA. Use [rubric.md](references/rubric.md) and [prompt-templates.md](references/prompt-templates.md). Rubric dimensions: correctness, safety, idempotency, traceability, spec compliance, RCA quality. Safety score `0` aborts immediately.

Persist GCL traces to `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` with secrets masked as `***`.

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Integration and Commands](references/integration.md)
- [Troubleshooting and RCA](references/troubleshooting.md)
- [AIOps Analysis](references/aiops.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

