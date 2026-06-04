# Rubric — azure-loadbalancer-ops

> GCL rubric for Azure Load Balancer operations.
> See `AGENTS.md §3` for dimension definitions and thresholds.

## Dimensions

| Dimension | Scale | Default threshold | Destructive threshold (LB delete / rule delete / probe delete / backend pool delete) |
|-----------|-------|-------------------|----------------------------------------------------------------------------------------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Safety** | 0 / 1 | = 1 | = 1 |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | = 1.0 |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | ≥ 0.5 |

**Safety = 0 → ABORT immediately.**

## Operation-Specific Scoring Guidance

### Create Load Balancer
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | LB created with correct name/RG/location/SKU/type; provisioning = Succeeded | LB created but type/SKU mismatch | LB not created or wrong subscription |
| Safety | Pre-flight: VNet (internal) or Public IP (public) verified; SKU (Basic vs Standard) confirmed | Pre-flight partially done | No pre-flight checks |
| Idempotency | Retry with same params errors `AlreadyExists` (safe — idempotent) | N/A | Retry causes duplicate (impossible — name unique) |
| Traceability | Full command + stdout + stderr + `az network lb show` verify | Partial capture | No trace saved |
| Spec Compliance | Follows `core-concepts.md` + `azure-cli-conventions.md`; RG required; `--sku` correct | Minor deviation | Hallucinated flag or missing RG |

### Delete Load Balancer
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | LB deleted; `az network lb show` returns `ResourceNotFound` | Wrong LB shown first | Wrong LB deleted |
| Safety | Explicit human confirmation exact LB name; `az network lb show` before delete; **traffic impact** communicated (all rules, probes, backend pools stop serving) | Show ran but no traffic impact warning | No confirmation at all |
| Idempotency | Second delete returns `ResourceNotFound` (idempotent) | Second attempt errors but safe | N/A |
| Traceability | Full trace: show → confirm → delete → verify | Delete only, no show | No trace |

### Delete / Modify Load Balancing Rule
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Rule deleted/updated; `az network lb rule list` confirms | Wrong rule modified | Wrong rule deleted |
| Safety | **Rule delete**: confirmed + traffic impact (ports/protocol) communicated | Warning but no confirmation | Deleted without confirmation |
| Idempotency | Delete already-deleted rule returns not-found (safe) | N/A | N/A |
| Traceability | Full trace: list-rules → confirm → delete/update → verify | Verify skipped | No trace |

### Delete Health Probe
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Probe deleted; `az network lb probe list` confirms | Wrong probe deleted | Wrong probe or error |
| Safety | Check if probe is referenced by any rule; if so, warn about health-check loss | Referenced but not warned | Deleted while in use |
| Idempotency | Delete already-deleted probe returns not-found (safe) | N/A | N/A |
| Traceability | Full trace: list-probes → confirm → delete → verify | Verify skipped | No trace |

### Add / Remove Backend Pool / VM
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | Pool added or VM added/removed; `address-pool list` confirms | Added but wrong VM | Wrong pool or error |
| Safety | **Remove VM from pool**: confirmed + traffic disruption (VM will stop receiving traffic) | Warning but no confirmation | Removed without confirmation |
| Idempotency | Add same VM again idempotent (duplicate ignored) | N/A | Remove causes cascade |
| Traceability | Full trace: list → confirm → modify → verify | Verify skipped | No trace |

### Create / Delete Inbound NAT Rule
| Dimension | 1.0 (pass) | 0.5 (partial) | 0 (fail) |
|-----------|------------|----------------|----------|
| Correctness | NAT rule created/deleted; `inbound-nat-rule list` confirms | Created but wrong port mapping | Wrong rule or error |
| Safety | **Delete**: confirmed + port forwarding impact | Warning but no confirmation | Deleted without confirmation |
| Idempotency | Create same NAT rule again idempotent (errors as duplicate) | N/A | N/A |
| Traceability | Full trace + verify | Verify skipped | No trace |

## Checklist (Critic Must Verify)

Before scoring, the Critic MUST verify:

- [ ] **Variables resolved**: no raw `{{env.*}}` / `{{user.*}}` in executed commands
- [ ] **RG present**: every `az network lb` command includes `--resource-group`
- [ ] **Location valid**: uses Azure naming (e.g. `eastus`)
- [ ] **LB delete confirmation**: `az network lb show` before delete; traffic impact communicated; exact name confirmation
- [ ] **Rule delete**: traffic impact (port/protocol) communicated before rule delete
- [ ] **Probe delete**: checked if referenced by any rule; health-check loss warned
- [ ] **VM removal from pool**: traffic disruption (VM stops receiving traffic) warned
- [ ] **NAT rule delete**: port forwarding impact communicated
- [ ] **SKU clear**: Basic vs Standard confirmed with user (Standard has different features: HA ports, zone-redundancy, NSG required)
- [ ] **Public vs Internal**: type confirmed with user (determines pre-flight checks)
- [ ] **JSON output**: `--output json` on every CLI command (except `-o tsv` for ID extraction)
- [ ] **Error handling**: recovery table consulted; HALT vs retry decision recorded
- [ ] **No credential leak**: output does not contain `AZURE_CLIENT_SECRET` or connection strings