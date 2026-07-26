# AIOps — Load Balancer RCA Rules

> AIOps-driven root cause analysis for Azure Load Balancer anomalies.

## Detection Signals

| Signal | Source | Description |
|--------|--------|-------------|
| probe_failure | `az network lb probe show` | Health probe detects backend down |
| snat_exhaustion | `az monitor metrics list` --metric "SNAT Connection Count" | SNAT ports depleted |
| datapath_unavailable | `az monitor metrics list` --metric "DipAvailability" | Data path to backend unavailable |

## RCA Rules

### Rule: Health Probe Failure
```
trigger: probe_failure
flow:
  1. Show probe status: az network lb probe show --name <probe> --lb-name <lb> --resource-group <rg>
  2. Check backend pool members: az network lb address-pool list --lb-name <lb> --resource-group <rg>
  3. Verify probe port and protocol match backend service
  4. If probe correct: check backend VM/container health independently
  5. Check NSG rules allowing probe traffic (Azure LB uses 168.63.129.16)
```

### Rule: SNAT Port Exhaustion
```
trigger: snat_exhaustion
flow:
  1. Check SNAT port usage: az monitor metrics list --resource <lb_id> --metric "SNAT Connection Count"
  2. Check number of backend instances
  3. If outbound connections per instance > 64K: recommend adding more instances
  4. Consider: using outbound rules with port allocation, or NAT Gateway
```

### Rule: Data Path Unavailability
```
trigger: datapath_unavailable
flow:
  1. Check backend pool availability: az network lb address-pool list --lb-name <lb>
  2. Check if backend VMs are running: az vm list --resource-group <rg>
  3. Check VNet/subnet configuration
  4. If backend in different region: LB is region-scoped, check cross-region LB

## Cross-Skill Integration

See `docs/cross-skill-rca-schema.md` for standard diagnostic paths and cross-service root cause analysis chains.

When this skill detects an anomaly that may involve other services:
- Delegate to `azure-monitor-ops` for metric correlation and Activity Log investigation
- Follow the standard diagnostic path defined in `docs/cross-skill-rca-schema.md`
```