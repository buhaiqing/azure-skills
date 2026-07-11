# Rubric — azure-apim-ops

> GCL rubric for Azure API Management operations.
> See `AGENTS.md §3` for dimension definitions and thresholds.

## Dimensions

| Dimension | Scale | Default threshold | Destructive threshold (APIM/API/Product/Subscription delete; key regenerate; policy overwrite) |
|-----------|-------|-------------------|--------------------------------------------------------------------------------------------------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Safety** | 0 / 1 | = 1 | = 1 |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |

**Safety = 0 → ABORT immediately.**

## Operation-Specific Scoring Guidance

### Create APIM Instance
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | APIM created with correct name/RG/location/SKU; provisioningState=Succeeded; gatewayUrl populated | APIM created but SKU mismatch | APIM not created or wrong subscription |
| Safety | Pre-flight: name uniqueness verified (`check-name`); RG/location valid; publisher_email/publisher_name non-empty | Pre-flight not all verified | No pre-flight |
| Idempotency | Retry returns existing APIM or `ResourceNameInvalid` (safe failure); same-name update is idempotent | N/A | Retry creates duplicate (impossible — name is globally unique) |
| Traceability | Full command + LRO status polled to terminal + `az apim show` verify | LRO not polled | No trace |
| Spec Compliance | Follows `core-concepts.md` + `azure-cli-conventions.md`; `--sku-name` matches `SkuType` enum; `--output json` present | Minor deviation (e.g., location inferred but valid) | Hallucinated flag or missing RG |

### Delete APIM / API / Product / Subscription
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Resource deleted; `show` returns `ResourceNotFound`; `az apim deletedservice list` shows soft-deleted APIM | Wrong resource shown first | Wrong resource deleted |
| Safety | Explicit exact-name confirmation; `show` before delete; **traffic impact** warning (APIM delete = all gateways stop serving all clients) | Show ran but no traffic impact warning | No confirmation |
| Idempotency | Second delete returns `ResourceNotFound` (idempotent) | Second attempt errors but safe | N/A |
| Traceability | Full trace: show → confirm → delete → verify (or `az apim deletedservice list`) | Delete only, no show | No trace |

### Create / Update API
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | API created/updated; `az apim api show` confirms display_name, path, service_url | Created but path mismatch | API not created |
| Safety | service_url belongs to expected backend; subscription_required true for public APIs | service_url not verified | API exposes backend without auth gate |
| Idempotency | Re-running create returns same API (idempotent) | N/A | Duplicate APIs created |
| Traceability | Full trace with revision number (revision 1, 2, ...) | Verify skipped | No trace |

### Create / Update Product
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Product created/updated; `az apim product show` confirms display_name, state | Created but state wrong (e.g., `notPublished` when `published` expected) | Product not created |
| Safety | `subscription_required=true` for non-public products; `approval_required` confirmed with user | Mode not clarified | Product published with no subscription gate |
| Idempotency | Re-running create returns same product | N/A | Duplicate products |
| Traceability | Full trace: create → verify | Verify skipped | No trace |

### Add API to Product
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | API added; `az apim product api list` confirms | Added but display name wrong | API not associated |
| Safety | API and product exist; product is published (else add has no effect) | N/A | N/A |
| Idempotency | Adding same API to same product is idempotent (already exists) | N/A | Duplicate association |
| Traceability | Full trace: list → add → verify | Verify skipped | No trace |

### Create / Delete Subscription (SDK ONLY)
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Subscription created/deleted; `client.subscription.get` confirms state and scope | Created but scope wrong | Subscription not created |
| Safety | **Primary/secondary keys NEVER in trace**; scope = `/products/{product-id}` (not `/apis/{api-id}` directly); `state=active` confirmed | Keys in trace but masked | Keys visible in command args, stdout, or trace |
| Idempotency | Re-creating same subscription with same sid returns same record | N/A | Duplicate subscriptions |
| Traceability | Full SDK call + get + verify; **keys redacted** | Verify skipped | Keys leaked |

### Regenerate Subscription Key (SDK ONLY)
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Key regenerated; `list_secrets` returns new primary_key | N/A | Regenerate failed |
| Safety | **Old key value NEVER in trace**; user explicitly warned about client invalidation; coordinated rollout if possible | Warning but no confirmation | Regenerated without confirmation or key leaked |
| Idempotency | Calling regenerate twice produces two distinct keys (intended behavior) | N/A | N/A |
| Traceability | Full SDK call + post-regenerate `list_secrets` invocation; **new key value masked** | Verify skipped | New key leaked |

### Apply Policy — Global / API / Product (SDK ONLY)
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Policy applied; `client.{policy,api_policy,product_policy}.get` returns the new XML | Applied but `format` wrong (rawxml vs xml) | Policy not applied |
| Safety | **Policy XML NEVER in full trace** if it contains `value=` secrets (connection strings, AAD secrets); mask or omit value attributes; warning: immediate traffic impact acknowledged | Warning but no confirmation | Policy overwrite without warning, or secrets in trace |
| Idempotency | Re-applying same policy is idempotent | N/A | N/A |
| Traceability | Full SDK call + get + verify; XML redacted if contains secrets | Verify skipped | XML with secrets leaked |

### List / Show
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | List/show returns expected results; `provisioningState=Succeeded` verified for show | Wrong filter | Empty/wrong subscription |
| Safety | Subscription keys filtered out of show output (`--query` or post-filter) | N/A | Keys leaked |
| Idempotency | List/show are inherently idempotent | N/A | N/A |
| Traceability | Full command + output | N/A | No trace |

## Checklist (Critic Must Verify)

Before scoring, the Critic MUST verify:

- [ ] **Variables resolved**: no raw `{{env.*}}` / `{{user.*}}` in executed commands
- [ ] **RG present**: every CLI command includes `--resource-group`
- [ ] **Location valid**: uses Azure naming (e.g., `eastus`)
- [ ] **APIM name uniqueness**: `az apim check-name` ran before create
- [ ] **Publisher email/name**: non-empty, valid email format
- [ ] **SKU name valid**: matches `SkuType` enum — CLI path accepts `Consumption / Developer / Basic / Standard / Premium / Isolated`; SDK path additionally accepts `BasicV2 / StandardV2` (BasicV2/StandardV2 only via SDK, not CLI)
- [ ] **JSON output**: `--output json` on every CLI command
- [ ] **LRO polling**: SDK `begin_*().result()` calls complete before proceeding
- [ ] **Safety gate on delete**: `show` before delete + traffic impact warning + exact-name confirmation
- [ ] **Subscription keys**: NOT visible in command args, stdout, or trace (masked if shown)
- [ ] **Policy XML secrets**: `<set-* value="...">` attributes masked in trace; `<connection-string>`, `<aad-client-secret>`, `<signing-key>` values redacted
- [ ] **CLI gap respected**: subscription/policy operations use SDK; CLI used only where `az apim` exposes commands
- [ ] **Error handling**: recovery table consulted; HALT vs retry decision recorded
- [ ] **No credential leak**: output does not contain `AZURE_CLIENT_SECRET`, subscription primary/secondary keys, or policy XML secret values
- [ ] **RBAC role**: Contributor role verified for write operations
- [ ] **Soft-delete awareness**: APIM delete is recoverable for 48h via `az apim deletedservice list`