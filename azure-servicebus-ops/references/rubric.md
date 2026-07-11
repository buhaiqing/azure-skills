# Azure Service Bus GCL Rubric

Use this rubric for destructive Service Bus operations and recommended incident RCA reviews.

## Dimensions

| Dimension | Scale | Threshold | Service Bus Criteria |
|-----------|-------|-----------|---------------------|
| Correctness | 0 / 0.5 / 1 | >= 0.5; 1 for delete/key rotation | Correct resource ID, namespace/queue/topic/subscription name, Resource Group, Location, SKU, and requested operation; metrics/fields verified |
| Safety | 0 / 1 | = 1 | Required confirmations obtained; no secrets exposed; high-risk actions gated |
| Idempotency | 0 / 0.5 / 1 | >= 0.5 | Safe retries only; no repeated delete/key rotation; state re-read after timeout |
| Traceability | 0 / 0.5 / 1 | >= 0.5 | Commands/SDK calls, parameters, output excerpts, errors, correlation IDs recorded |
| Spec Compliance | 0 / 0.5 / 1 | >= 0.5 | Follows Azure CLI primary + SDK fallback, Resource Group/Location terminology, HALT-vs-retry rules |
| RCA Quality | 0 / 0.5 / 1 | >= 0.5 for incidents | Evidence precedes conclusion, confidence stated, safe vs approval-required actions separated |

Safety `0` aborts immediately.

## Required Checks for High-Risk Service Bus Actions

| Action | Must Verify |
|--------|-------------|
| Delete namespace | exact name/RG confirmation, latest resource state, impact statement (all queues/topics/subscriptions lost) |
| Delete queue/topic/subscription | exact name/RG/namespace confirmation, impact on consumers |
| Regenerate keys | primary/secondary choice, rotation plan, client update plan, confirmation |
| Purge DLQ | data-loss warning, exact confirmation, fallback expectation |
| Modify TTL/delivery count | current vs proposed values, impact on message lifecycle, confirmation |
| Modify filter rules | impact on message routing, confirmation |

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
- operation could delete/purge/rotate keys without confirmation;
- evidence contradicts the requested remediation.
