# Azure Network Security Group GCL Rubric

Rubric version: `v1`

| Dimension | Scale | Passing Threshold | NSG-Specific Criteria |
|-----------|-------|-------------------|-----------------------|
| Correctness | 0 / 0.5 / 1 | ≥ 0.5; 1.0 required for delete, dissociate, broad allow/deny changes | Resource Group, Location, NSG name, rule name, priority, direction, access, protocol, prefixes, ports, and target association match request |
| Safety | 0 / 1 | = 1 | Destructive or exposure-changing actions have explicit human confirmation; Safety=0 means ABORT |
| Idempotency | 0 / 0.5 / 1 | ≥ 0.5 | Re-running does not create duplicate rules, overwrite unrelated rules, or detach unintended associations |
| Traceability | 0 / 0.5 / 1 | ≥ 0.5 | Command/SDK call, parameters, output IDs, effective rules, errors, and confirmation evidence are captured with secrets masked |
| Spec Compliance | 0 / 0.5 / 1 | ≥ 0.5 | Uses Azure CLI primary, SDK fallback after retry, Resource Group and Location terms, full resource IDs, and `{{env.*}}` / `{{user.*}}` / `{{output.*}}` placeholders |

## Blocking Conditions

Return `blocking: true` when any condition applies:

- Safety score is 0.
- Delete or dissociation lacks exact-name or exact-resource-ID confirmation.
- Rule mutation uses guessed priority, source, destination, port, access, or direction.
- The target Resource Group or full association resource ID is ambiguous.
- Credentials or raw secrets appear in output or trace.

## PASS Criteria

A run passes only when every dimension meets its threshold and no blocking condition exists.
