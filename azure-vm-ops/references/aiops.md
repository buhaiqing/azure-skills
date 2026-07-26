# AIOps — Virtual Machine RCA Rules

> AIOps-driven root cause analysis for Azure VM anomalies.

## Detection Signals

| Signal | Source | Description |
|--------|--------|-------------|
| vm_cpu_high | `az monitor metrics list` --metric "Percentage CPU" | CPU > 90% for > 10min |
| vm_memory_pressure | `az monitor metrics list` --metric "Available Memory Bytes" | Available memory < 500MB |
| vm_disk_latency | `az monitor metrics list` --metric "Disk Read/Write Latency" | Latency > 50ms sustained |
| vm_unexpected_restart | `az monitor activity-log list` | VM restart without user action |
| run_command_failure | `az vm run-command invoke` exit code non-zero | RunCommand execution failure |

## RCA Rules

### Rule: High CPU Root Cause
```
trigger: vm_cpu_high
flow:
  1. Check top processes: az vm run-command invoke --command-id RunShellScript --scripts "top -bn1 | head -20"
  2. Check if CPU correlates with recent deployment: az monitor activity-log list --resource-id <id> --start-time <1h_ago>
  3. Check network traffic spike: az monitor metrics list --resource <id> --metric "Network In/Out"
  4. If process is known (app server, DB): recommend scaling up or optimizing
  5. If process unknown: flag for security investigation
```

### Rule: Disk Latency Diagnosis
```
trigger: vm_disk_latency > 50ms for > 5min
flow:
  1. Check disk queue depth: az vm run-command invoke --scripts "iostat -x 1 3"
  2. Check disk type (SSD/HDD): az vm show --resource-group <rg> --name <vm>
  3. If Premium SSD and high queue: recommend increasing disk IOPS
  4. If Standard HDD: recommend upgrade to SSD
```

### Rule: Unexpected Restart Investigation
```
trigger: vm_unexpected_restart detected
flow:
  1. Check Activity Log for restart source: az monitor activity-log list --resource-id <id>
  2. Check if Azure initiated (planned maintenance): check correlationId for Azure events
  3. Check VM agent health: az vm get-instance-view --resource-group <rg> --name <vm>
  4. If guest OS crash: recommend checking Event Log / syslog
```

### Rule: RunCommand Failure Handling
```
trigger: run_command_failure
flow:
  1. Check VM agent status: az vm get-instance-view --resource-group <rg> --name <vm>
  2. If agent not ready: wait 30s and retry (max 3 times)
  3. If command syntax error: validate command before retry
  4. If timeout: increase --timeout value
```

## Cross-Skill Integration

See `docs/cross-skill-rca-schema.md` for standard diagnostic paths and cross-service root cause analysis chains.

When this skill detects an anomaly that may involve other services:
- Delegate to `azure-monitor-ops` for metric correlation and Activity Log investigation
- Follow the standard diagnostic path defined in `docs/cross-skill-rca-schema.md`