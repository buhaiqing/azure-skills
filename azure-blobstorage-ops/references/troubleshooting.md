# Azure Blob Storage Troubleshooting Guide

## Common API Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| InvalidParameter | 400 | Request validation failed | Fix args per Azure REST API docs |
| InvalidResourceName | 400 | Storage account/container name invalid | Fix naming convention |
| StorageAccountAlreadyExists | 409 | Storage account name taken | Use different name |
| StorageAccountNotFound | 404 | Storage account does not exist | Verify account name and RG |
| ContainerNotFound | 404 | Container does not exist | Create container or fix name |
| BlobNotFound | 404 | Blob does not exist | Verify blob name |
| AuthenticationFailed | 403 | Invalid credentials or permissions | Check keys/SAS/Azure AD |
| AuthorizationFailed | 403 | RBAC permission insufficient | Add required role |
| AccessDenied | 403 | Public access disabled or insufficient | Check access configuration |
| QuotaExceeded | 400/402 | Storage limit reached | HALT; request quota increase |
| ServiceQuotaExceededException | 400 | Request rate exceeded | Retry with exponential backoff |
| ThrottlingException | 429 | Rate limit exceeded | Backoff, retry 3x |
| InternalError | 500 | Azure service error | Retry 3x; HALT with correlation ID |
| ServiceUnavailable | 503 | Service temporarily down | Retry 3x; HALT |
| OperationTimedOut | 500 | Operation timeout | Retry with smaller operations |

## Diagnostic Order

### Storage Account Issues

1. **Verify credentials**: `az account show`
2. **Verify subscription**: Check `AZURE_SUBSCRIPTION_ID`
3. **Verify resource group**: `az group show --name {{rg}}`
4. **Get storage account**: `az storage account show --name {{account}} --resource-group {{rg}}`
5. **Check account status**: Verify provisioning state
6. **List account keys**: `az storage account keys list`
7. **Test connectivity**: Try container list operation

### Container Issues

1. **List containers**: `az storage container list --account-name {{account}}`
2. **Show container**: `az storage container show --name {{container}} --account-name {{account}}`
3. **Check access level**: Review public access setting

### Blob Issues

1. **List blobs**: `az storage blob list --account-name {{account}} --container-name {{container}}`
2. **Show blob**: `az storage blob show --name {{blob}} --container-name {{container}} --account-name {{account}}`
3. **Check blob properties**: Verify size, type, content type

## Storage Account Creation Issues

### Issue: Storage account name already exists

**Symptoms**:
- Creation fails with "StorageAccountAlreadyExists"
- Name conflicts globally

**Resolution**:
```bash
# Storage account names are globally unique
# Use a unique name with prefix/suffix pattern
az storage account create --name "{{unique_prefix}}{{suffix}}" --resource-group {{rg}} ...
```

### Issue: Invalid storage account name

**Symptoms**:
- Error: "InvalidResourceName"
- Name contains invalid characters

**Resolution**:
- Name must be 3-24 characters
- Only lowercase letters and numbers
- No spaces, hyphens, underscores

### Issue: Quota exceeded

**Symptoms**:
- Creation fails with quota error
- Regional limit reached

**Resolution**:
```bash
# Check current usage
az storage account list --output json | jq 'length'

# Request quota increase via Azure support portal
# Or use different subscription/region
```

## Authentication Issues

### Issue: Authentication failed

**Symptoms**:
- Operations fail with "AuthenticationFailed"
- Cannot access storage account

**Diagnosis Steps**:
1. Verify account keys: `az storage account keys list`
2. Check if keys were rotated
3. Verify SAS token validity
4. Check Azure AD permissions

**Resolution Options**:
| Cause | Resolution |
|-------|------------|
| Invalid account key | Get fresh key: `az storage account keys list` |
| Expired SAS token | Generate new SAS token |
| Azure AD permission missing | Add Storage Blob Data Contributor role |

### Issue: Access denied

**Symptoms**:
- "AccessDenied" or "AuthorizationFailed"
- Cannot read/write blobs

**Resolution**:
```bash
# Check public access setting
az storage account show --name {{account}} --query "allowBlobPublicAccess"

# If Azure AD, verify RBAC assignment
az role assignment list --assignee {{user-id}} --output json

# Add required role
az role assignment create \
  --assignee {{user-id}} \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.Storage/storageAccounts/{{account}}"
```

## Container Issues

### Issue: Container not found

**Symptoms**:
- Operations fail with "ContainerNotFound"
- Container does not exist

**Resolution**:
```bash
# Create container first
az storage container create --name {{container}} --account-name {{account}}

# Or verify container exists
az storage container list --account-name {{account}} --query "[?name=='{{container}}']"
```

### Issue: Cannot create container

**Symptoms**:
- Container creation fails
- Error message about access

**Resolution**:
```bash
# Verify account key is valid
az storage account keys list --account-name {{account}} --query "[0].value"

# Use explicit account key
az storage container create \
  --name {{container}} \
  --account-name {{account}} \
  --account-key {{key}}
```

## Blob Upload Issues

### Issue: Blob upload failed

**Symptoms**:
- Upload timeout or failure
- Large file upload fails

**Diagnosis Steps**:
1. Check file size (large files need block upload)
2. Verify network connectivity
3. Check storage account capacity

**Resolution Options**:
```bash
# For large files, use AzCopy (optimized for large transfers)
azcopy copy "{{local_file}}" "https://{{account}}.blob.core.windows.net/{{container}}/{{blob}}?{{sas_token}}"

# Or upload in blocks
az storage blob upload \
  --account-name {{account}} \
  --container-name {{container}} \
  --name {{blob}} \
  --file {{file}} \
  --max-block-size 100MB \
  --block-blob-tier Hot
```

### Issue: Blob type mismatch

**Symptoms**:
- Cannot modify blob
- Wrong blob type for operation

**Resolution**:
- Block blob: Most file types
- Append blob: Log files (append only)
- Page blob: VHD files (random write)

## Blob Download Issues

### Issue: Download timeout

**Symptoms**:
- Download hangs or fails
- Large blob download fails

**Resolution**:
```bash
# Use AzCopy for large downloads
azcopy copy "https://{{account}}.blob.core.windows.net/{{container}}/{{blob}}?{{sas_token}}" "{{local_path}}"

# Or chunk download
az storage blob download \
  --account-name {{account}} \
  --container-name {{container}} \
  --name {{blob}} \
  --file {{file}}
```

### Issue: Blob not found during download

**Symptoms**:
- "BlobNotFound" error
- File doesn't exist

**Resolution**:
```bash
# Verify blob exists
az storage blob list --account-name {{account}} --container-name {{container}} --query "[?name=='{{blob}}']"

# Check if blob was deleted (soft delete)
az storage blob list --account-name {{account}} --container-name {{container}} --include d
```

## Performance Issues

### Issue: Slow upload/download

**Symptoms**:
- High latency in operations
- Transfer rates are slow

**Resolution Options**:
- Use Premium storage account for high performance
- Use AzCopy for parallel transfers
- Check network bandwidth
- Use appropriate blob tier
- Consider using CDN for public read-heavy blobs

## Soft Delete Issues

### Issue: Recovering deleted blob

**Symptoms**:
- Blob was accidentally deleted
- Need to recover data

**Resolution**:
```bash
# List deleted blobs (if soft delete enabled)
az storage blob list \
  --account-name {{account}} \
  --container-name {{container}} \
  --include d

# Restore deleted blob
az storage blob undelete \
  --account-name {{account}} \
  --container-name {{container}} \
  --name {{blob}}
```

## Activity Log for Debugging

```bash
# Check storage account operations
az monitor activity-log list \
  --resource "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.Storage/storageAccounts/{{account}}" \
  --output json
```

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Data loss/corruption | Critical | Immediate Azure support ticket |
| Production data inaccessible | Critical | Immediate support ticket |
| Security breach indicator | Critical | Immediate support + security review |
| Persistent authentication issues | High | Support ticket with error details |
| Quota/capacity issues | Medium | Quota increase request via portal |
| Performance degradation | Medium | Performance analysis + support |
| Feature clarification | Low | Azure forums or documentation |