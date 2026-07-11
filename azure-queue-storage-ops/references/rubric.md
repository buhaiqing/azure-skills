# Rubric — azure-queue-storage-ops

> GCL rubric for Azure Queue Storage operations.
> See `AGENTS.md §3` for dimension definitions and thresholds.

## Dimensions

| Dimension | Scale | Default threshold | Destructive threshold (queue delete / clear queue) |
|-----------|-------|-------------------|-----------------------------------------------------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Safety** | 0 / 1 | = 1 | = 1 |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |

**Safety = 0 → ABORT immediately.**

## Operation-Specific Scoring Guidance

### Create Queue
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Queue created with correct name; `az storage queue show` returns it | Queue created but metadata mismatch | Queue not created or wrong storage account |
| Safety | Pre-flight all passed; account key not leaked | Pre-flight partial | No pre-flight checks |
| Idempotency | Retry with same name errors `QueueAlreadyExists` (safe) | N/A | Retry causes duplicate (impossible — names unique per storage account) |
| Traceability | Full command + stdout + stderr + verify | Partial capture | No trace saved |
| Spec Compliance | Follows `core-concepts.md`; name 3-63 chars lowercase; RG required | Minor deviation | Hallucinated flag or missing RG |

### Delete Queue
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Queue deleted; `az storage queue show` returns `QueueNotFound` | Wrong queue shown first | Wrong queue deleted |
| Safety | Explicit human confirmation exact queue name; `az storage queue show` before delete; approximate message count shown for data-loss warning | Show ran but no data-loss warning | No confirmation at all |
| Idempotency | Second delete returns `QueueNotFound` (idempotent) | Second attempt errors but safe | N/A |
| Traceability | Full trace: show → get message count → confirm → delete → verify | Delete only, no data-loss warning | No trace |

### Clear Queue
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | All messages cleared; `az storage queue show` returns approximate_message_count = 0 | Queue cleared but verify skipped | Wrong queue cleared |
| Safety | Explicit confirmation; approximate message count shown for data-loss warning; account-key handled securely | Confirmation but no message count | No confirmation |
| Idempotency | Second clear returns success (idempotent) | N/A | N/A |
| Traceability | Full trace: show → get count → confirm → clear → verify | Verify skipped | No trace |

### Enqueue Message
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Message enqueued; `az storage message peek` confirms content and message_id | Enqueued but content mismatch | Enqueue failed or wrong queue |
| Safety | Message size check (64 KB limit); account key not leaked | Size not explicitly checked | Message too large and no warning |
| Idempotency | Re-sending same message creates duplicate (expected — queue storage is at-least-once) | N/A | N/A |
| Traceability | Full command + output + peek verify | Verification skipped | No trace |

### Dequeue / Peek Message
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Messages dequeued/peeked; content matches; pop_receipt and message_id captured | Dequeued but no output parsed | Dequeue failed or wrong queue |
| Safety | No mutation on peek; dequeue visibility timeout set appropriately; account key not leaked | Timeout too short for expected processing | N/A |
| Idempotency | Multiple peeks return same messages (idempotent); multiple dequeues return different batches | N/A | N/A |
| Traceability | Full command + output + message count captured | Output not parsed | No trace |

### Update Message (Visibility Timeout)
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Visibility timeout updated; next peek confirms new timeout | Updated but wrong timeout value | Update failed (bad pop_receipt) |
| Safety | Only extends timeout (not destructive); account key not leaked | N/A | N/A |
| Idempotency | Re-updating same message with same pop_receipt may fail (pop_receipt consumed on update) | N/A | N/A |
| Traceability | Full command + output + verify | Verify skipped | No trace |

### Delete Message
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Message deleted; next peek confirms message gone | Wrong message deleted | Delete failed (bad pop_receipt) |
| Safety | Message_id and pop_receipt verified; account key not leaked | Pop_receipt not double-checked | No verification |
| Idempotency | Second delete returns `MessageNotFound` (safe — message already gone) | N/A | N/A |
| Traceability | Full trace: message_id → pop_receipt → delete → verify | Verify skipped | No trace |

### List / Show Operations
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Correct listing with filters applied | Listed but missing filter | Wrong listing or error |
| Safety | No mutation; safe | N/A | N/A |
| Idempotency | Multiple list calls identical | N/A | N/A |
| Traceability | Command + output captured | Output not parsed | No trace |

### Account Key Handling
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Safety | Account key fetched into shell variable (`$ACCOUNT_KEY`), used in `--account-key` param, **never echoed to stdout or trace** | Key fetched but stored in trace | Key printed to stdout / leaked into trace output |

## Checklist (Critic Must Verify)

Before scoring, the Critic MUST verify:

- [ ] **Variables resolved**: no raw `{{env.*}}` / `{{user.*}}` in executed commands
- [ ] **RG present**: every `az storage account *` command includes `--resource-group`
- [ ] **Location valid**: uses Azure naming (e.g. `eastus`)
- [ ] **Queue name valid**: 3-63 chars, lowercase alphanumeric and hyphens only
- [ ] **Queue delete confirmation**: `az storage queue show` + approximate message count (data-loss warning) before delete; exact queue name confirmation
- [ ] **Clear queue confirmation**: approximate message count shown; queue name confirmed
- [ ] **Message delete**: pop_receipt verified before delete
- [ ] **Account key safety**: `ACCOUNT_KEY` stored in shell variable, **never printed to stdout or trace**; only `--account-key "$ACCOUNT_KEY"` usage visible
- [ ] **JSON output**: `--output json` on every CLI command (except `-o tsv` for key extraction, which is acceptable)
- [ ] **Error handling**: recovery table consulted; HALT vs retry decision recorded
- [ ] **No credential leak**: output does not contain `AZURE_CLIENT_SECRET`, account keys, or connection strings
- [ ] **Message size**: enqueue checks message size < 64 KB limit
