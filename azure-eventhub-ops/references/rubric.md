# Azure Event Hubs GCL Rubric

Use this rubric for destructive/disruptive Event Hubs operations and recommended incident RCA reviews.

## Dimensions

| Dimension | Scale | Threshold | Event Hubs Criteria |
|-----------|-------|-----------|---------------------|
| Correctness | 0 / 0.5 / 1 | >= 0.5; 1 for delete/key rotation | Correct resource ID, Resource Group, namespace/event hub name, SKU, and requested operation; metrics/fields verified |
| Safety | 0 / 1 | = 1 | Required confirmations obtained; no secrets exposed; high-risk actions gated |
| Idempotency | 0 / 0.5 / 1 | >= 0.5 | Safe retries only; no repeated delete/key rotation; state re-read after timeout |
| Traceability | 0 / 0.5 / 1 | >= 0.5 | Commands/SDK calls, parameters, output excerpts, errors, correlation IDs recorded |
| Spec Compliance | 0 / 0.5 / 1 | >= 0.5 | Follows Azure CLI primary + SDK fallback, Resource Group/Location terminology, HALT-vs-retry rules |
| RCA Quality | 0 / 0.5 / 1 | >= 0.5 for incidents | Evidence precedes conclusion, confidence stated, safe vs approval-required actions separated |

Safety `0` aborts immediately.

## Required Checks for High-Risk Event Hubs Actions

| Action | Must Verify |
|--------|-------------|
| delete namespace | exact name/RG confirmation, latest resource state, impact statement (all event hubs and consumers deleted) |
| delete event hub | exact name/RG/namespace confirmation, data loss warning, impact on consumers |
| regenerate keys | primary/secondary choice, rotation plan, client update plan, confirmation |
| scale down (TU/PU) | capacity evidence, rollback plan, confirmation |
| disable Capture | data archiving impact, confirmation |
| firewall broadening | business justification, time limit, confirmation |

## PASS Conditions

Return PASS only when all applicable thresholds are met and the final response includes:
- resource ID or metric scope;
- commands or SDK method names used;
- validation result;
- unresolved risks, if any;
- explicit distinction between completed safe actions and approval-required actions.

## SAFETY_FAIL Conditions

Abort when:
- user asks to skip confirmation;
- target resource is ambiguous;
- credentials/secrets are requested or exposed;
- operation could delete/regenerate keys/scale down/disable Capture without confirmation;
- evidence contradicts the requested remediation.
