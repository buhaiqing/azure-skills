# Core Concepts — azure-audit-ops

> Cross-product audit skill. Covers Activity Log, RBAC, Locks, Diagnostic Settings, Policy, and Security posture.

## Audit Categories

| Category | Azure Service | CLI Prefix | Purpose |
|----------|--------------|------------|---------|
| **Activity Log** | Azure Monitor | `az monitor activity-log` | Who did what, when, and with what result |
| **RBAC** | Azure RBAC | `az role assignment / definition` | Who has access to what, at what scope |
| **Resource Locks** | Azure Resource Manager | `az lock` | Prevent accidental deletion/modification |
| **Diagnostic Settings** | Azure Monitor | `az monitor diagnostic-settings` | Are logs flowing to Log Analytics / Event Hub? |
| **Policy** | Azure Policy | `az policy` | Compliance state, non-compliant resources |
| **Security Posture** | Various | Varies | Public endpoints, NSG rules, encryption |
| **Resource Inventory** | Azure Resource Graph | `az resource` / `az graph` | What resources exist, their configuration |

## Activity Log Overview

The Activity Log records **control-plane** (management) operations at subscription scope. It includes:

- **Administrative**: Create/Update/Delete resources (`Microsoft.Compute/virtualMachines/write`)
- **Security**: Policy assignments, role assignments (`Microsoft.Authorization/roleAssignments/write`)
- **Service Health**: Azure platform events
- **Autoscale**: Autoscale engine operations
- **Alert**: Alert firings
- **Recommendation**: Advisor recommendations
- **Policy**: Policy effect evaluation

**Retention**: Stored for 90 days by default. Can be exported to Log Analytics or Storage Account for longer retention.

## RBAC Concepts

| Role | Type | Scope | Risk |
|------|------|-------|------|
| **Owner** | Built-in | All resources | Full access — can delegate to others |
| **Contributor** | Built-in | All resources | Create/manage but cannot delegate |
| **Reader** | Built-in | All resources | Read-only (safe) |
| **Custom Roles** | Custom | Defined by author | Varies — review permissions |

**Key audit checks**:
- Owner/Contributor at subscription scope (over-privileged)
- Service Principals with broad access
- Orphaned role assignments (deleted users/SPs)
- Custom roles with wildcard actions (`*`)

## Resource Lock Types

| Lock | Effect | Audit Signal |
|------|--------|-------------|
| **CanNotDelete** | Authorized users can read/modify but NOT delete | Production resources without this lock |
| **ReadOnly** | Authorized users can read only (no modifications) | Resources that should be immutable |
| No lock | No protection | Exists on most resources — find the critical ones |

Locks are applied at **subscription**, **resource group**, or **resource** scope. Children inherit from parent.

## Diagnostic Settings

Diagnostic settings stream **control-plane** and **data-plane** logs/metrics to:

| Destination | Use Case |
|-------------|----------|
| **Log Analytics workspace** | Query, alert, analyze all logs centrally |
| **Storage Account** | Low-cost archive, long-term retention |
| **Event Hub** | Stream to SIEM (Sentinel, Splunk) |

**Audit signal**: Resources without diagnostic settings → monitoring gap.

## Azure Policy

| Concept | Description |
|---------|-------------|
| **Policy definition** | Individual rule (e.g. "Allowed locations") |
| **Initiative** (Policy Set) | Group of policies (e.g. "CIS Benchmark") |
| **Assignment** | Applies a definition/initiative to a scope |
| **Compliance state** | Compliant / Non-compliant / Unknown / Not started |

**Compliance states**:
- **Compliant**: Resource matches policy
- **NonCompliant**: Resource violates policy
- **Conflict**: Two or more policies conflict
- **Exempt**: Resource explicitly exempted

## Security Posture Checks

| Check | CLI Command | Risk |
|-------|-------------|------|
| Public blob access | `az storage account list --query "[?allowBlobPublicAccess==\`true\`]"` | Data exposure |
| VMs with public IPs | `az vm list` + NIC inspection | Unrestricted inbound access |
| NSG broad rules | `az network nsg list --query "[?securityRules[?access=='Allow' && sourceAddressPrefix=='*']]"` | Unrestricted inbound |
| AKS RBAC disabled | `az aks list --query "[?enableRBAC==\`false\`]"` | No Kubernetes RBAC |
| SQL firewall broad | `az sql server firewall-rule list` | Data exposure |
| Key Vault soft-delete | `az keyvault list --query "[?enableSoftDelete==null]"` | Accidental permanent deletion |

## Report Severity Levels

| Severity | Meaning | Example |
|----------|---------|---------|
| **Critical** | Immediate security/data risk | Public blob access, Owner at subscription scope |
| **High** | Significant operational risk | No CanNotDelete lock on production, non-compliant policy |
| **Medium** | Best practice gap | Missing diagnostic settings, missing tags |
| **Low** | Informational | Resource inventory count, tag naming inconsistency |

## Delegation

This skill is **read-only**. Remediation actions must be delegated:

| Audit Finding | Delegate To |
|---------------|-------------|
| Activity Log anomaly | `azure-monitor-ops` (create alert rule) |
| RBAC over-privileged | `az role assignment delete` (inline) or `azure-rbac-ops` |
| Missing resource lock | `az lock create` (inline) |
| Missing diagnostic settings | `azure-monitor-ops` |
| Public blob access | `azure-blobstorage-ops` |
| NSG rule too permissive | `azure-network-ops` |
| Policy non-compliant | `az policy remediation create` or fix resource config

## Audit Report Template

Findings are structured as a table:

| Category | Finding | Severity | Resource | Recommendation |
|----------|---------|----------|----------|----------------|
| RBAC | Contributor assignment at subscription scope for user@example.com | Medium | /subscriptions/... | Scope to resource group |
| Security | Storage account myaccount has public blob access enabled | High | /subscriptions/.../storageAccounts/... | Disable public access |
| Lock | Resource group prod-rg has no CanNotDelete lock | Medium | /subscriptions/.../resourceGroups/prod-rg | Add CanNotDelete lock |
| Diagnostic | VM my-vm has no diagnostic settings configured | Low | /subscriptions/.../virtualMachines/... | Enable diagnostics |
| Policy | 3 resources non-compliant with "Require tag" policy | Medium | (varies) | Apply required tags |

## Delegation Rules (detailed)

| Finding | Delegate To | Action |
|---------|-------------|--------|
| Missing diagnostic settings | `azure-monitor-ops` | Create diagnostic setting |
| Public blob access | `azure-blobstorage-ops` | Update `--allow-blob-public-access false` |
| Missing resource lock | `azure-resourcelock-ops` or direct `az lock create` | Add CanNotDelete lock |
| Unrestricted NSG rule | `azure-network-ops` | Update NSG rule |
| RBAC misconfiguration | `azure-rbac-ops` or `az role assignment create/delete` | Fix role assignment |
| Non-compliant policy | (varies by policy) | Follow specific skill |