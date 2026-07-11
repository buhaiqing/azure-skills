# Azure Site Recovery Troubleshooting

## Replication Health Issues

### Synchronization Lag

| Symptom | Likely Cause | Diagnostic Command | Action |
|---------|-------------|-------------------|--------|
| "ReplicationNotProgressing" | Source VM disk I/O bottleneck | `az site-recovery protected-item show --name {{user.protected_item_name}} -g {{user.resource_group}} --vault-name {{user.vault_name}}` | Check `properties.providerSpecificDetails.lastReplicatedTime` |
| "DeltaReplicationPending" | Large data changes exceeding bandwidth | `az site-recovery job list --vault-name {{user.vault_name}} -g {{user.resource_group}}` | Check pending changes; throttle source writes |
| "SynchronizationStateNotSynchronized" | Network disconnection | `az site-recovery fabric check-consistency --fabric-name {{user.fabric_name}} -g {{user.resource_group}} --vault-name {{user.vault_name}}` | Check network connectivity between sites |

### Replication Stalled / Failed

| Symptom | Likely Cause | Diagnostic | Action |
|---------|-------------|------------|--------|
| "Critical" health | Mobility service not responding | `az site-recovery protected-item show --name {{user.protected_item_name}}` | Restart Mobility service on source VM |
| "AgentExpired" | Mobility service version outdated | Check agent version in portal | Update Mobility service via `begin_update_mobility_service` |
| "DiskNotFound" | Source disk detached | `az vm show --name {{user.vm_name}} -g {{user.resource_group}}` | Reattach disk; repair replication |
| "VmidNotFoundException" | VM deleted in source | `az vm list -g {{user.resource_group}}` | HALT; VM must be re-created |

## Failover Failure Root Causes

### Test Failover Failures

| Symptom | Cause | Action |
|---------|-------|--------|
| "TestFailoverNotSupported" | VM size not available in target | Check target region SKU availability |
| "TestFailoverCleanupRequired" | Prior test failover not cleaned up | Use Azure SDK `begin_test_failover_cleanup()` (CLI not supported) |
| "NetworkNotFound" | Test VNet missing | Create isolated VNet in target region |
| "IPAddressConflict" | Test IP conflicts with production | Use isolated subnet with different address space |

### Failover Commit Failures

| Symptom | Cause | Action |
|---------|-------|--------|
| "FailoverCommitNotAllowed" | Protected item not in failover state | Check `properties.activeLocation` |
| "ProtectedItemNotFound" | Item deleted during failover | List items; verify name |
| "TargetVMDeploymentFailed" | Quota exceeded in target region | HALT; request quota increase |
| "ExtensionInstallationFailed" | Azure VM agent not ready | Wait for VM agent; check agent status |

### Planned Failover Failures

| Symptom | Cause | Action |
|---------|-------|--------|
| "PlannedFailoverNotSupported" | VM not in running state | Start source VM |
| "PlannedFailoverSyncFailed" | Shutdown script timeout | Check VM shutdown; retry with longer timeout |
| "PlannedFailoverInProgress" | Another failover running | Wait for completion or cancel |

## Recovery Plan Issues

| Issue | Cause | Resolution |
|-------|-------|------------|
| Group stuck | Pre/post script failure | Check script execution; bypass failed step |
| VM order wrong | Group assignment incorrect | Update recovery plan group order |
| Runbook not executed | Automation account not linked | Link automation account; check runbook |
| SQL Availability Group failover fails | Listener not configured | Check AG listener setup; verify DNS |

## Job Issues

| Symptom | Cause | Action |
|---------|-------|--------|
| Job stuck at 99% | Async operation timeout | Wait; check `az site-recovery job show` |
| Job cancelled | Manual cancel or conflict | Resume job or restart operation |
| Job failed with unknown error | Internal platform error | Retry; contact support if persistent |

## Recovery Table

| Error | Action |
|-------|--------|
| ReplicationNotProgressing | Check source VM I/O; reduce churn |
| DeltaReplicationPending | Increase bandwidth; throttle writes |
| AgentExpired | Update Mobility service |
| TestFailoverCleanupRequired | Run SDK `begin_test_failover_cleanup()` first |
| TargetVMDeploymentFailed | HALT; request quota increase |
| NetworkNotFound | Create VNet in target region |
| QuotaExceeded | HALT; request quota increase |
| InvalidParameter | Fix args; retry once |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |
| ResourceNotFound | Verify resource name and RG; list available resources |
| AccessDenied (403) | HALT; check RBAC permissions |
