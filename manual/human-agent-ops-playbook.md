# Human–Agent Ops Playbook

End-to-end Azure operations with azure-skills (MS L400 Business strategy).

## Flow

```
Symptom → orchestrator diagnose → risk tier → GCL (if R1/R2)
        → auto_feedback_loop (R0/R1) → verify → CADL finding
        → escalate (R2 or heal exhausted)
```

## Steps

### 1. Diagnose (cross-skill)

```bash
python3 scripts/orchestrator.py --diagnose "AKS node not ready"
python3 scripts/orchestrator.py --heal azure-aks-ops "node_pool_expansion_failed"
```

### 2. Confirm risk tier

```bash
python3 scripts/risk_tiers.py --skill azure-aks-ops --operation aks_delete
# R2 → stop; get human confirmation before any delete
```

### 3. Execute with quality gate

```bash
# R1 example — GCL recommended
python3 scripts/gcl_runner.py --skill azure-vm-ops --critic rule -- ...

# L4 loop (non-risky)
python3 scripts/auto_feedback_loop.py \
  --skill azure-vm-ops \
  --operation vm_create \
  --command "az vm create ..." \
  --desired-state '{"powerState":"VM running"}'
```

### 4. Proactive path (alerts)

```bash
python3 scripts/watch_and_heal.py --alerts-file scripts/sample_alerts.json --dry-run
```

### 5. Verify & report

```bash
python3 scripts/health_dashboard.py --azure-monitor   # payload always written
python3 scripts/value_report.py
```

## Human confirmation wording (R2)

Require an explicit phrase such as: `I confirm delete of <resource-id>`.
Never pass `--risky` to bypass without that confirmation in the session.

## Related

- [l4闭环](./l4闭环.md) · [orchestrator](./orchestrator.md) · [governance-federation](./governance-federation.md)
