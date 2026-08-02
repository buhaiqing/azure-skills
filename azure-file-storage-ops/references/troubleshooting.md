# Azure File Storage Troubleshooting Guide

## Common API Error Codes

| Code (HTTP) | Meaning -> Action |
|-------------|-------------------|
| InvalidParameter (400) | Request validation failed -> Fix args per Azure REST API docs |
| InvalidResourceName (400) | Share name invalid -> Fix naming convention (3-63 chars, lowercase + hyphens) |
| ShareAlreadyExists (409) | Share name already exists in this account -> Use different name |
| ShareNotFound (404) | Share does not exist -> Verify share name and account |
| AuthenticationFailed (403) | Invalid credentials or permissions -> Check keys/SAS/Azure AD |
| AuthorizationFailed (403) | RBAC permission insufficient -> Add required role |
| AccessDenied (403) | Access denied -> Check network rules or key validity |
| QuotaExceeded (400/402) | Storage limit reached -> HALT; request quota increase |
| ThrottlingException (429) | Rate limit exceeded -> Backoff, retry 3x |
| InternalError (500) | Azure service error -> Retry 3x; HALT with correlation ID |
| ServiceUnavailable (503) | Service temporarily down -> Retry 3x; HALT |
| ShareSnapshotConflict (409) | Snapshot operation conflict -> Retry after existing snapshot settles |
| ShareBeingDeleted (409) | Share in deletion state -> Wait and retry |
| FeatureNotSupportedForShare (400) | Operation not supported for NFS shares -> Switch to SMB or check protocol compatibility |

## Diagnostic Order

### File Share Issues
1. **Verify credentials**: `az account show`
2. **Verify storage account**: `az storage account show --name {{user.storage_account_name}} --resource-group {{user.resource_group}}`
3. **List shares**: `az storage share list --account-name {{user.storage_account_name}} --account-key "$KEY"`
4. **Show share**: `az storage share show --name {{user.share_name}} --account-name {{user.storage_account_name}} --account-key "$KEY"`
5. **Check quota**: Verify `share_quota` in show output
6. **Check network**: Test connectivity to `{{user.storage_account_name}}.file.core.windows.net` on port 445 (SMB) or 2049 (NFS)

## Mount Issues

### Issue: Windows cannot mount SMB share

**Symptoms**:
- Error "System error 53" or "Network path not found"
- Cannot map drive letter

**Diagnosis Steps**:
1. Test connectivity: `Test-NetConnection {{user.storage_account_name}}.file.core.windows.net -Port 445`
2. Verify port 445 is open (often blocked by ISPs/corporate firewalls)
3. Check if storage account key is correct

**Resolution Options**:
| Cause | Resolution |
|-------|------------|
| Port 445 blocked | Use VPN or ExpressRoute; or use Azure File Sync |
| Wrong credentials | Use `az storage account keys list` to get fresh key |
| Share not accessible | Verify share exists and key has permissions |

### Issue: Linux cannot mount SMB share

**Symptoms**:
- `mount error(13): Permission denied`
- Cannot access mount point

**Resolution**:
```bash
# Install cifs-utils
sudo apt-get install cifs-utils  # Ubuntu/Debian
sudo yum install cifs-utils      # RHEL/CentOS

# Mount SMB share
sudo mount -t cifs \
  //{{user.storage_account_name}}.file.core.windows.net/{{user.share_name}} \
  /mnt/{{user.mount_point}} \
  -o vers=3.0,username={{user.storage_account_name}},password={{output.account_key}},dir_mode=0777,file_mode=0777,serverino
```

### Issue: Linux cannot mount NFS share

**Symptoms**:
- `mount.nfs: Connection timed out`
- NFS mount fails

**Resolution**:
```bash
# Install nfs-common
sudo apt-get install nfs-common  # Ubuntu/Debian
sudo yum install nfs-utils       # RHEL/CentOS

# Mount NFS share (requires premium FileStorage account)
sudo mount -t nfs \
  {{user.storage_account_name}}.file.core.windows.net:/{{user.storage_account_name}}/{{user.share_name}} \
  /mnt/{{user.mount_point}} \
  -o vers=4,minorversion=1,sec=sys,nconnect=4
```

## Quota Issues

### Issue: Share quota needs to be increased

**Symptoms**:
- Write failures with "disk full" errors
- Share shows 100% usage in quota

**Resolution**:
```bash
# Check current quota
az storage share show --name {{user.share_name}} --account-name {{user.storage_account_name}} --query "properties.shareQuota"

# Increase quota (max 5120 GB for standard, 102400 GB with large file shares enabled)
az storage share update \
  --name {{user.share_name}} \
  --account-name {{user.storage_account_name}} \
  --quota {{user.quota_gb}}
```

### Issue: Quota exceeds limit

**Symptoms**:
- `QuotaExceeded` error on update
- Cannot increase beyond maximum

**Resolution**:
- Standard shares: max 5 TiB default, 100 TiB with quota increase request
- Premium shares: max 100 TiB
- Request increase via Azure support portal

## Snapshot Issues

### Issue: Cannot create snapshot

**Symptoms**:
- Snapshot creation fails
- Feature not supported error

**Resolution**:
- NFS shares do not support snapshots via NFS protocol
- Ensure share exists and is accessible
- Check for concurrent snapshot operations

### Issue: Recovering from snapshot

**Symptoms**:
- Files accidentally deleted or modified
- Need to restore from snapshot

**Resolution**:
```bash
# List snapshots
az storage share list \
  --account-name {{user.storage_account_name}} \
  --include-snapshots \
  --query "[?name=='{{user.share_name}}']"

# Mount snapshot (read-only) via UNC path with snapshot time
# \\{{user.storage_account_name}}.file.core.windows.net\{{user.share_name}}\?sharesnapshot={{user.snapshot_time}}
```

## Soft Delete Issues

### Issue: Recovering a deleted share

**Symptoms**:
- Share was accidentally deleted
- Need to restore

**Resolution** (SDK required — CLI does not support undelete directly):
```python
from azure.mgmt.storage import StorageManagementClient

client = StorageManagementClient(credential, subscription_id)

# List deleted shares
from azure.mgmt.storage.models import ListSharesExpand
shares = client.file_shares.list(
    resource_group_name='{{user.resource_group}}',
    account_name='{{user.storage_account_name}}',
    expand='deleted'
)

# Find deleted share version
for s in shares:
    if s.name == '{{user.share_name}}' and s.deleted:
        version = s.version

# Restore share
from azure.mgmt.storage.models import DeletedShare
client.file_shares.restore(
    resource_group_name='{{user.resource_group}}',
    account_name='{{user.storage_account_name}}',
    share_name='{{user.share_name}}',
    deleted_share=DeletedShare(
        deleted_share_name='{{user.share_name}}',
        deleted_share_version=version
    )
)
```

## Sync Issues (Azure File Sync)

### Issue: Files not syncing

**Symptoms**:
- Changes not propagating between servers
- Sync health shows error

**Resolution**:
- Check server endpoint health in Azure Portal
- Verify File Sync agent is up-to-date
- Check for file conflicts or locked files
- Review File Sync telemetry

### Issue: Cloud tiering issues

**Symptoms**:
- Files unexpectedly tiered to cloud
- Performance degradation

**Resolution**:
- Adjust cloud tiering policy (date/volume free space %)
- Ensure sufficient local cache space
- Recall files: `fsutil file recall <filepath>`

## Performance Issues

### Issue: Slow file transfer

**Symptoms**:
- Low throughput on uploads/downloads
- High latency

**Resolution Options**:
- Use premium FileStorage tier for consistent performance
- Use multiple threads/parallel connections
- Check network bandwidth and latency
- Use AzCopy for bulk transfers
- Enable SMB Multichannel for multi-NIC clients

## Activity Log for Debugging

```bash
# Check file share operations
az monitor activity-log list \
  --resource "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Storage/storageAccounts/{{user.storage_account_name}}/fileServices/default/shares/{{user.share_name}}" \
  --output json
```

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Data loss/corruption | Critical | Immediate Azure support ticket |
| Production shares inaccessible | Critical | Immediate support ticket |
| Security breach indicator | Critical | Immediate support + security review |
| Persistent mount failures | High | Support ticket with error details |
| Quota/capacity issues | Medium | Quota increase request via portal |
| Sync health degraded | Medium | Review File Sync telemetry + support |
| Performance degradation | Medium | Performance analysis + support |
