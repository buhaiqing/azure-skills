# Rubric — azure-vnet-ops

> GCL rubric for Azure Virtual Network operations. See `AGENTS.md §3` for dimension definitions and thresholds.

## Dimensions

| Dimension | Scale | Default threshold | Destructive / connectivity-impact threshold |
|-----------|-------|-------------------|---------------------------------------------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Safety** | 0 / 1 | = 1 | = 1 |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |

**Safety = 0 → ABORT immediately.**

## Operation-Specific Scoring Guidance

### Create Virtual Network / Subnet

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | VNet/subnet created with correct Resource Group, Location, CIDR, and provisioningState `Succeeded` | Created but optional DNS/service endpoint/delegation mismatch | Wrong subscription, Resource Group, or CIDR |
| Safety | Resource Group, Location, and CIDR overlap checked | Some pre-flight checks skipped but no mutation risk found | No pre-flight checks |
| Idempotency | Re-run detects existing resource and updates safely or reports AlreadyExists | Re-run needs manual interpretation | Re-run creates unintended resource |
| Traceability | Command, args, stdout, stderr, exit code, and validation captured | Partial trace | No trace |
| Spec Compliance | Uses `az network vnet` commands with `--output json`; SDK fallback documented | Minor omission | Hallucinated flag or missing Resource Group |

### Delete Virtual Network / Subnet

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Target deleted; show returns `ResourceNotFound` | Delete accepted but not verified | Wrong VNet/subnet deleted |
| Safety | Show dependencies first; warn impact; exact-name human confirmation | Warning present but dependency detail incomplete | No confirmation or dependencies ignored |
| Idempotency | Second delete is safe `ResourceNotFound` | N/A | Cascade/dependency delete attempted without review |
| Traceability | Full trace: dependency show → confirm → delete → verify | Delete and verify only | No trace |
| Spec Compliance | Uses Resource Group and full VNet/subnet identity | Minor omission | Missing Resource Group or wrong resource type |

### Address Space / Subnet Prefix Update

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Updated CIDR contains required subnets and does not overlap peers | Update works but overlap evidence incomplete | Invalid or disruptive CIDR applied |
| Safety | Existing subnets, peerings, and dependencies checked; user confirms impact | Checks incomplete | Prefix changed without impact warning |
| Idempotency | Re-run results in same address plan | N/A | Re-run drifts configuration |
| Traceability | Before/after address spaces captured | Partial before/after | No trace |

### VNet Peering

| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Peering created/updated/deleted on intended VNet(s); state verified | One direction only when bidirectional expected | Wrong VNet peered or broken |
| Safety | Overlap, permissions, and traffic impact checked; destructive peering removal confirmed | Some checks missing | Peering removed without warning |
| Idempotency | Re-run detects existing peering safely | N/A | Duplicate/conflicting peering created |
| Traceability | Both local and remote VNet IDs captured | Only names captured | No trace |

## Checklist (Critic Must Verify)

- [ ] Variables resolved; no raw `{{env.*}}` / `{{user.*}}` in executed commands
- [ ] Every VNet command includes `--resource-group` where required
- [ ] Azure term **Location** used and validated
- [ ] `--output json` used on CLI commands except explicit `-o tsv` queries
- [ ] CIDR is valid and does not overlap existing VNets or peered networks
- [ ] Subnet prefix is inside VNet address space
- [ ] Delete operations show dependencies and require exact-name confirmation
- [ ] Address prefix changes include before/after trace and impact warning
- [ ] Peering changes include both VNet IDs and connectivity impact warning
- [ ] Recovery table consulted; HALT vs retry recorded
- [ ] No credential leak: `AZURE_CLIENT_SECRET`, tokens, or connection strings absent from trace
