# Azure Backup Troubleshooting

## Backup Failure Root Causes

### VM Snapshot Timeout

| Symptom | Likely Cause | Diagnostic Command | Action |
|---------|-------------|-------------------|--------|
| "SnapshotTimeout" | VM has high disk I/O | `az backup job show --name {{user.job_name}}` | Check `properties.extendedInfo.propertyBag` for error details |
| "ExtensionSnapshotFailed" | VSS writer issue (Windows) | Check VM event logs via RunCommand | Restart VSS service; retry backup |
| "ExtensionSnapshotFailed" | Pre-post script failure (Linux) | Check `/var/log/azure/Microsoft.Azure.RecoveryServices.SnapshotLinux/` logs | Fix script; retry |
| "DiskNotFound" | VM disk detached or deleted | `az vm show --name {{user.vm_name}}` | Reattach disk or reconfigure backup |

### SQL / SAP HANA Log Chain Break

| Symptom | Likely Cause | Diagnostic | Action |
|---------|-------------|------------|--------|
| "UserErrorSQLPITPointInTimeRestoreNotPossible" | Log chain broken | Check SQL log backup history | Run full backup to restart chain |
| "UserErrorBackupFailedWithScriptFailure" | SQL VSS writer error | Check SQL Server error log | Restart SQL Server VSS Writer service |
| "WorkloadExtensionError" | Extension not responding | `az backup container list` | Re-register protection container |

### Network Errors

| Error Code | Cause | Action |
|------------|-------|--------|
| "ExtensionNetworkError" | VM cannot reach Azure Backup endpoints | Verify NSG allows `AzureBackup` service tag |
| "UserErrorVMInternetConnectivityIssue" | No internet/proxy access | Configure proxy settings in VM extension |
| "UserErrorBackupOperationNetworkFailure" | Intermittent network failure | Retry; check Azure Backup service health |

### Quota / Resource Limits

| Error | Cause | Action |
|-------|-------|--------|
| "UserErrorMaxVaultsReached" | 250 vaults per subscription | HALT; request quota increase |
| "UserErrorMaxProtectedItemsReached" | Per-vault item limit | HALT; create new vault or request increase |
| "UserErrorInsufficientStorage" | Backup storage exhausted | HALT; increase storage redundancy |

## Restore Failure Root Causes

| Symptom | Cause | Action |
|---------|-------|--------|
| "UserErrorRestoreTargetNotFound" | Target RG or storage deleted | Verify target resources exist |
| "UserErrorRestoreDiskTargetNotFound" | Managed disk quota exceeded | HALT; request quota increase |
| "UserErrorRestorePointNotFound" | Recovery point expired or deleted | List available points; select valid one |
| "UserErrorRestoreTargetNetworkNotFound" | Target VNet/Subnet missing | Create or specify existing VNet |

## Retention Policy Issues

| Issue | Cause | Resolution |
|-------|-------|------------|
| Backup taking too much storage | Retention too long | Review and adjust retention policy |
| Old recovery points unexpectedly missing | Retention policy expired | Verify `properties.retentionPolicy` settings |
| Soft-delete items not visible | Soft-delete window expired (14 days) | Check before expiry; permanent after |

## Recovery Table

| Error | Action |
|-------|--------|
| SnapshotTimeout | Retry after reducing VM disk I/O; check VSS writers |
| ExtensionNetworkError | Verify NSG `AzureBackup` tag; check proxy |
| WorkloadExtensionError | Re-register container; restart extension |
| QuotaExceeded | HALT; request quota increase |
| InvalidParameter | Fix args; retry once |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |
| ResourceNotFound | Verify resource name and RG; list available resources |
| AccessDenied (403) | HALT; check RBAC permissions |
