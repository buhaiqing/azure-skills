# Rubric — azure-blobstorage-ops

> GCL rubric for Azure Blob Storage operations.
> See `AGENTS.md §3` for dimension definitions and thresholds.

## Dimensions

| Dimension | Scale | Default threshold | Destructive threshold (account delete / container delete / blob delete) |
|-----------|-------|-------------------|-----------------------------------------------------------------------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Safety** | 0 / 1 | = 1 | = 1 |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |

**Safety = 0 → ABORT immediately.**

## Operation-Specific Scoring Guidance

### Create Storage Account
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Account created with correct name/RG/location/SKU/kind; provisioning = Succeeded | Account created but SKU/kind mismatch | Account not created or wrong subscription |
| Safety | Pre-flight all passed; `--allow-blob-public-access false` and `--min-tls-version TLS1_2` used for security | Security defaults not all applied | Public access allowed by default |
| Idempotency | Retry with same params errors `StorageAccountAlreadyExists` (safe — idempotent) | N/A | Retry causes duplicate (impossible — names are globally unique) |
| Traceability | Full command + stdout + stderr + `az storage account show` verify | Partial capture | No trace saved |
| Spec Compliance | Follows `core-concepts.md` + `azure-cli-conventions.md`; name 3-24 chars; RG required | Minor deviation | Hallucinated flag or missing RG |

### Delete Storage Account
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Account deleted; `az storage account show` returns `ResourceNotFound` | Wrong account shown first | Wrong account deleted |
| Safety | Explicit human confirmation exact account name; `az storage account show` before delete; **containers listed** to warn about data loss | Show ran but no data-loss warning | No confirmation at all |
| Idempotency | Second delete returns `ResourceNotFound` (idempotent) | Second attempt errors but safe | N/A |
| Traceability | Full trace: show → list-containers → confirm → delete → verify | Delete only, no data-loss warning | No trace |

### Delete Blob Container
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Container deleted; `az storage container show` returns `NotFound` | Wrong container shown first | Wrong container deleted |
| Safety | Explicit confirmation; blobs listed first to warn about data loss; account-key handled securely (not leaked) | Confirmation but no blob listing | No confirmation |
| Idempotency | Second delete returns `NotFound` (idempotent) | N/A | N/A |
| Traceability | Full trace: show → list-blobs → confirm → delete → verify | Verify skipped | No trace |

### Delete Blob
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Blob deleted; `az storage blob show` returns `BlobNotFound` | Wrong blob shown first | Wrong blob deleted |
| Safety | Explicit confirmation; `az storage blob show` before delete; account-key handled securely | Confirmation but no show | No confirmation |
| Idempotency | Second delete errors `BlobNotFound` (safe) | N/A | N/A |
| Traceability | Full trace: show → confirm → delete → verify | Verify skipped | No trace |

### Upload / Download Blob
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | File uploaded/downloaded successfully; `blob show` confirms size/etag match | Uploaded but checksum not verified | Upload failed or wrong file |
| Safety | No overwrite without `--overwrite true` confirmed; account-key not leaked | Overwrite warned but implied consent | Overwritten without any warning |
| Idempotency | Re-upload same file idempotent (if `--overwrite true`) | N/A | N/A |
| Traceability | Full command + progress + verification | Verification skipped | No trace |

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
- [ ] **Account name valid**: 3-24 chars, lowercase alphanumeric only
- [ ] **Security defaults**: `--allow-blob-public-access false` set; `--min-tls-version TLS1_2` preferred
- [ ] **Account delete confirmation**: `az storage account show` + `az storage container list` (data-loss warning) before delete; exact account name confirmation
- [ ] **Container delete confirmation**: blobs listed first to warn about data loss; container name confirmed
- [ ] **Blob delete confirmation**: `az storage blob show` before delete; blob name confirmed
- [ ] **Overwrite gate**: `--overwrite true` only used after explicit user consent
- [ ] **Account key safety**: `ACCOUNT_KEY` stored in shell variable, **never printed to stdout or trace**; only `--account-key "$ACCOUNT_KEY"` usage visible
- [ ] **JSON output**: `--output json` on every CLI command (except `-o tsv` for key extraction, which is acceptable)
- [ ] **Error handling**: recovery table consulted; HALT vs retry decision recorded
- [ ] **No credential leak**: output does not contain `AZURE_CLIENT_SECRET`, account keys, or connection strings
- [ ] **SKU tier clear**: `Standard_LRS` vs `Standard_GRS` confirmed with user if not specified