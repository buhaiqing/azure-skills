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

This is a **cross-product read-only audit skill**. It inspects Azure resources for security,
compliance, configuration completeness, and operational hygiene. It does NOT mutate resources.
If a finding requires remediation, the skill delegates the fix to the appropriate service skill
(e.g. `azure-monitor-ops` for diagnostic settings, `azure-blobstorage-ops` for public access).

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

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse; optional for subscription-level audit |
| `{{user.target_resource_id}}` | User input | Specific resource to audit |
| `{{user.time_range}}` | User input | Time range for activity log (e.g. "7d", "2026-05-01T00:00:00Z/2026-06-01T00:00:00Z") |
| `{{output.activity_log_entries}}` | Last API response | Parsed activity log entries |
| `{{output.audit_report}}` | Last API response | Structured audit findings |

## Execution Flow Pattern

Every audit follows: **Scope → Collect → Analyze → Report**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Scope     │ → │   Collect   │ → │   Analyze   │ → │   Report    │
│  Definition │    │    Data     │    │   Findings  │    │  & Actions  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Audit 1: Activity Log Review (Who did what)

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `az --version` | Install Azure CLI 2.0+ |
| Credentials | `az account show` | HALT; configure env |
| Subscription valid | `az account list --output json` | Suggest valid subscription |

#### Execute — Azure CLI (Primary)
```bash
# Recent subscription-level activity
az monitor activity-log list \
  --start-time "{{user.time_range_start}}" \
  --end-time "{{user.time_range_end}}" \
  --output json

# Filter by caller (user/SP)
az monitor activity-log list \
  --caller "{{user.caller_upn}}" \
  --start-time "{{user.time_range_start}}" \
  --end-time "{{user.time_range_end}}" \
  --output json

# Filter by operation
az monitor activity-log list \
  --operation "Microsoft.Compute/virtualMachines/write" \
  --start-time "{{user.time_range_start}}" \
  --output json

# Filter by resource group
az monitor activity-log list \
  --resource-group "{{user.resource_group}}" \
  --start-time "{{user.time_range_start}}" \
  --output json

# Filter by event severity
az monitor activity-log list \
  --severity Error \
  --start-time "{{user.time_range_start}}" \
  --output json

# Top-N summary: who did what, how many times
az monitor activity-log list \
  --start-time "{{user.time_range_start}}" \
  --query "[].{Caller:caller, Operation:operationName.value, Time:eventTimestamp}" \
  --output json
```

#### Execute — Azure SDK (Fallback)
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.monitor import MonitorManagementClient
from datetime import datetime, timedelta
import os

credential = DefaultAzureCredential()
client = MonitorManagementClient(
    credential,
    subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID')
)

# Query activity log
end_time = datetime.utcnow()
start_time = end_time - timedelta(days=7)

activity_log = client.activity_logs.list(
    filter=f"eventTimestamp ge '{start_time.isoformat()}Z' and eventTimestamp le '{end_time.isoformat()}Z'",
    select='caller,operationName,eventTimestamp,status'
)

for event in activity_log:
    print(f"{event.caller}: {event.operation_name.value} @ {event.event_timestamp}")
```

#### Validate
```bash
# Verify query returned data
az monitor activity-log list --max-events 1 --output json
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidTimeRange | Fix time format; retry once |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |

### Audit 2: RBAC / Role Assignment Audit

```bash
# List all role assignments in subscription
az role assignment list --output json

# List role assignments for specific user/SP
az role assignment list --assignee "{{user.principal_id}}" --output json

# List role assignments in resource group
az role assignment list --resource-group "{{user.resource_group}}" --output json

# List custom roles
az role definition list --custom-role-only true --output json

# Check for privileged roles (Owner, Contributor) at subscription scope
az role assignment list --include-inherited \
  --query "[?roleDefinitionName=='Owner' || roleDefinitionName=='Contributor']" \
  --output json
```

### Audit 3: Resource Lock Audit

```bash
# List all resource locks at subscription level
az lock list --output json

# List resource locks in resource group
az lock list --resource-group "{{user.resource_group}}" --output json

# Check if a specific resource has a lock (CanNotDelete / ReadOnly)
az lock list --resource "{{user.target_resource_id}}" --output json

# Find resources without locks
# List resource groups, then cross-check lock existence
az group list --query "[].name" -o tsv | while read rg; do
  locks=$(az lock list --resource-group "$rg" --query "length(@)" -o tsv)
  echo "$rg: $locks lock(s)"
done
```

### Audit 4: Diagnostic Settings Completeness

```bash
# List diagnostic settings for a resource
az monitor diagnostic-settings list \
  --resource "{{user.target_resource_id}}" \
  --output json

# Find resources without diagnostic settings
# (Requires iterating through resources; SDK recommended for scale)
```

### Audit 5: Policy Compliance

```bash
# List all policy assignments
az policy assignment list --output json

# Get compliance state for subscription
az policy state list --output json

# Filter non-compliant resources
az policy state list \
  --filter "complianceState eq 'NonCompliant'" \
  --output json

# List policy definitions
az policy definition list --output json

# List initiatives (policy set definitions)
az policy set-definition list --output json
```

### Audit 6: Security Posture Review

```bash
# NSG rules audit — find rules with broad source access
az network nsg list --query "[].{Name:name, Rules:securityRules[?access=='Allow' && sourceAddressPrefix=='*' || sourceAddressPrefix=='Internet']}" --output json

# Storage accounts with public access allowed
az storage account list \
  --query "[?allowBlobPublicAccess==`true`].{Name:name, RG:resourceGroup}" \
  --output json

# VMs with public IPs
az vm list --query "[?networkProfile.networkInterfaces[?contains(id,'networkInterfaces')]].{Name:name, RG:resourceGroup}" --output json
# Then check each NIC's IP configuration for public IP association

# AKS clusters with RBAC disabled
az aks list --query "[?enableRBAC==`false`].{Name:name, RG:resourceGroup}" --output json

# SQL servers with firewall rules allowing all Azure services
az sql server firewall-rule list --server "{{user.sql_server}}" --resource-group "{{user.resource_group}}" \
  --query "[?startIpAddress=='0.0.0.0' && endIpActivity=='0.0.0.0']" --output json

# Key Vaults with soft-delete disabled
az keyvault list --query "[?enableSoftDelete==null || enableSoftDelete==`false`].{Name:name, RG:resourceGroup}" --output json
```

### Audit 7: Resource Inventory & Configuration Drift

```bash
# List all resources in subscription (inventory)
az resource list --output json

# List resources by type
az resource list --resource-type "Microsoft.Compute/virtualMachines" --output json

# Tag audit — find resources missing required tags
az resource list --query "[?tags==null || !tags.Environment || !tags.Owner].{Name:name, Type:type, RG:resourceGroup}" --output json

# Resource Group audit — RGs without locks or tags
az group list --query "[?tags==null || !tags.Environment].{Name:name, Location:location}" --output json
```

## Audit Report Template

Findings are structured as a table:

| Category | Finding | Severity | Resource | Recommendation |
|----------|---------|----------|----------|----------------|
| RBAC | Contributor assignment at subscription scope for user@example.com | Medium | /subscriptions/... | Scope to resource group |
| Security | Storage account myaccount has public blob access enabled | High | /subscriptions/.../storageAccounts/... | Disable public access |
| Lock | Resource group prod-rg has no CanNotDelete lock | Medium | /subscriptions/.../resourceGroups/prod-rg | Add CanNotDelete lock |
| Diagnostic | VM my-vm has no diagnostic settings configured | Low | /subscriptions/.../virtualMachines/... | Enable diagnostics |
| Policy | 3 resources non-compliant with "Require tag" policy | Medium | (varies) | Apply required tags |

## Delegation Rules

| Finding | Delegate To | Action |
|---------|-------------|--------|
| Missing diagnostic settings | `azure-monitor-ops` | Create diagnostic setting |
| Public blob access | `azure-blobstorage-ops` | Update `--allow-blob-public-access false` |
| Missing resource lock | `azure-resourcelock-ops` or direct `az lock create` | Add CanNotDelete lock |
| Unrestricted NSG rule | `azure-network-ops` | Update NSG rule |
| RBAC misconfiguration | `azure-rbac-ops` or `az role assignment create/delete` | Fix role assignment |
| Non-compliant policy | (varies by policy) | Follow specific skill |

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

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- [Azure Activity Log Docs](https://docs.microsoft.com/azure/azure-monitor/essentials/activity-log)
- [Azure RBAC Docs](https://docs.microsoft.com/azure/role-based-access-control/)
- [Azure Policy Docs](https://docs.microsoft.com/azure/governance/policy/)
- [Azure Resource Lock Docs](https://docs.microsoft.com/azure/azure-resource-manager/management/lock-resources)
- [Azure Security Benchmark](https://docs.microsoft.com/security/benchmark/azure/)
> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
