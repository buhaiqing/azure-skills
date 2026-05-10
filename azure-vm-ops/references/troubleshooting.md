# Azure Virtual Machine Troubleshooting Guide

## Common API Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| InvalidParameter | 400 | Request validation failed | Fix args per Azure REST API docs |
| InvalidParameterValue | 400 | VM size or image invalid | Check supported sizes/images |
| MissingParameter | 400 | Required field omitted | Add missing parameter |
| AccessDenied | 403 | RBAC permission insufficient | HALT; user updates RBAC role |
| AuthorizationFailed | 403 | Operation not permitted | HALT; check RBAC assignment |
| ResourceNotFound | 404 | VM or resource not found | Verify VM name and resource group |
| NotFound | 404 | Subscription/resource group not found | Verify subscription ID |
| Conflict | 409 | VM already exists or state conflict | Check current VM state |
| QuotaExceeded | 400/402 | VM quota limit reached | HALT; user requests quota increase |
| ServiceQuotaExceededException | 400 | Regional quota limit | HALT; request support ticket |
| ThrottlingException | 429 | Rate limit exceeded | Retry with exponential backoff |
| RequestLimitExceeded | 429 | Too many requests | Backoff; reduce request rate |
| InternalError | 500 | Azure service error | Retry 3x; HALT with correlation ID |
| ServiceUnavailable | 503 | Service temporarily down | Retry 3x; HALT |
| VMSizeNotAvailable | 400 | VM size not available in location | Suggest alternative VM size |
| ImageNotFound | 400 | VM image not found | Suggest valid image |
| InsufficientCapacity | 500 | Azure capacity unavailable | Try different location/size |

## Diagnostic Order

### VM Provisioning Issues

1. **Verify credentials**: `az account show`
2. **Verify subscription**: Check `AZURE_SUBSCRIPTION_ID`
3. **Verify resource group**: `az group show --name {{rg}}`
4. **Get VM status**: `az vm show --name {{vm}} --resource-group {{rg}}`
5. **Check instance view**: `az vm get-instance-view --name {{vm}} --resource-group {{rg}}`
6. **Check Activity Log**: `az monitor activity-log list`
7. **Verify dependencies**: Check VNet, NIC, disk status

### VM Power State Issues

1. **Check power state**: `az vm get-instance-view --name {{vm}} --resource-group {{rg}} --query "statuses"`
2. **Check VM size**: Verify size is valid for region
3. **Check OS disk**: Verify disk is attached and healthy
4. **Check NIC**: Verify network interface is connected

## VM Creation Issues

### Issue: VM creation stuck in "Creating"

**Symptoms**:
- VM provisioning state stuck at "Creating"
- Long wait time (> 15 minutes)

**Diagnosis Steps**:
```bash
# Check VM status
az vm show --name {{vm}} --resource-group {{rg}} --output json

# Check instance view for detailed status
az vm get-instance-view --name {{vm}} --resource-group {{rg}} --output json

# Check Activity Log
az monitor activity-log list \
  --resource "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.Compute/virtualMachines/{{vm}}" \
  --output json
```

**Resolution Options**:
- Option A: Wait longer (complex configs take more time)
- Option B: Check Activity Log for specific error
- Option C: If stuck > 30 min, delete and retry
- Option D: Try different VM size

### Issue: VM creation failed - quota exceeded

**Symptoms**:
- "QuotaExceeded" or "ServiceQuotaExceededException"
- Regional vCPU limit reached

**Diagnosis Steps**:
```bash
# Check current usage
az vm list-usage --location {{location}} --output json

# Check quota for specific series
az vm list-skus --location {{location}} --size {{size}} --output json
```

**Resolution Options**:
- Option A: Request quota increase via Azure support portal
- Option B: Use different VM size series
- Option C: Use different region
- Option D: Use Spot VMs (different quota pool)

### Issue: VM size not available

**Symptoms**:
- "VMSizeNotAvailable" error
- Selected size not supported in region

**Resolution**:
```bash
# List available sizes in location
az vm list-skus --location {{location}} --output json

# Filter by category
az vm list-skus --location {{location}} --size Standard_DS --output json
```

### Issue: Image not found

**Symptoms**:
- "ImageNotFound" error
- Specified OS image unavailable

**Resolution**:
```bash
# List available images
az vm image list --location {{location}} --output json

# Search for specific publisher
az vm image list --publisher Canonical --location {{location}} --output json
```

## VM State Issues

### Issue: VM won't start

**Symptoms**:
- VM stuck in "Starting" state
- Start operation fails

**Diagnosis Steps**:
```bash
# Check VM instance view
az vm get-instance-view --name {{vm}} --resource-group {{rg}} --output json

# Check OS disk status
az disk show --name {{os_disk}} --resource-group {{rg}} --output json

# Check NIC status
az network nic show --name {{nic}} --resource-group {{rg}} --output json
```

**Common Causes**:
| Cause | Resolution |
|-------|------------|
| OS disk not attached | Reattach disk |
| Insufficient capacity | Try different size/location |
| Quota exceeded | Request quota increase |
| Internal Azure error | Retry or delete/recreate |

### Issue: VM stopped but still billed

**Symptoms**:
- VM shows "Stopped" state
- Billing continues

**Resolution**:
```bash
# Stop VM with deallocation (stops billing)
az vm stop --name {{vm}} --resource-group {{rg}} --output json

# Verify deallocation
az vm get-instance-view --name {{vm}} --resource-group {{rg}} --query "statuses[?code=='PowerState/deallocated']"
```

**Important**:
- "Stopped" (power off) = Still billed
- "Deallocated" = Not billed

### Issue: VM resize failed

**Symptoms**:
- Resize operation fails
- VM remains at old size

**Resolution**:
```bash
# Verify target size is available
az vm list-skus --location {{location}} --output json

# Resize requires deallocation first
az vm deallocate --name {{vm}} --resource-group {{rg}}
az vm resize --name {{vm}} --resource-group {{rg}} --size {{new_size}}
az vm start --name {{vm}} --resource-group {{rg}}
```

## Network Connectivity Issues

### Issue: Cannot SSH/RDP to VM

**Symptoms**:
- Connection timeout
- Authentication failure

**Diagnosis Steps**:
```bash
# Check public IP exists
az vm show --name {{vm}} --resource-group {{rg}} --query "networkProfile.networkInterfaces[0].id"

# Get public IP address
az network public-ip show --name {{pip}} --resource-group {{rg}} --query "ipAddress"

# Check NSG rules for SSH/RDP
az network nsg rule list --nsg-name {{nsg}} --resource-group {{rg}} --output json
```

**Resolution Options**:
| Cause | Resolution |
|-------|------------|
| NSG blocking port | Add inbound rule for SSH (22) or RDP (3389) |
| No public IP | Create public IP |
| VM stopped | Start VM |
| Firewall on VM | Check OS firewall settings |
| Wrong credentials | Reset password/SSH key |

### Issue: Reset SSH key/password

**Symptoms**:
- Cannot authenticate to VM
- Lost SSH key or password

**Resolution**:
```bash
# Reset SSH key (Linux)
az vm user reset-ssh \
  --name {{vm}} \
  --resource-group {{rg}} \
  --username {{user}} \
  --ssh-key-value "{{new_ssh_public_key}}"

# Reset password (Windows/Linux)
az vm user update \
  --name {{vm}} \
  --resource-group {{rg}} \
  --username {{user}} \
  --password "{{new_password}}"
```

## Disk Issues

### Issue: OS disk not found

**Symptoms**:
- VM creation fails due to disk issue
- VM won't start, disk error

**Resolution**:
```bash
# Check disk status
az disk list --resource-group {{rg}} --output json

# Verify disk is attached
az vm show --name {{vm}} --resource-group {{rg}} --query "storageProfile.osDisk"
```

### Issue: Disk resize failed

**Symptoms**:
- Cannot expand disk
- Resize operation fails

**Resolution**:
```bash
# Resize disk (requires VM deallocate for OS disk)
az vm deallocate --name {{vm}} --resource-group {{rg}}
az disk update --name {{disk}} --resource-group {{rg}} --size-gb {{new_size}}
az vm start --name {{vm}} --resource-group {{rg}}

# Expand filesystem inside VM (Linux)
# ssh to VM and run: resize2fs /dev/sda1
```

## Performance Issues

### Issue: VM slow or unresponsive

**Symptoms**:
- High CPU usage
- Slow response times
- Memory pressure

**Diagnosis Steps**:
```bash
# Check VM metrics via Azure Monitor
az monitor metrics list \
  --resource "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.Compute/virtualMachines/{{vm}}" \
  --metric "Percentage CPU,Available Memory Bytes" \
  --output json
```

**Resolution Options**:
- Option A: Resize to larger VM
- Option B: Optimize application
- Option C: Add more data disks
- Option D: Use Premium SSD

## Activity Log for Debugging

```bash
# Check recent VM operations
az monitor activity-log list \
  --resource "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.Compute/virtualMachines/{{vm}}" \
  --start-time "2026-05-10T00:00:00Z" \
  --output json

# Check by caller
az monitor activity-log list \
  --caller "{{user-or-sp}}" \
  --resource-provider Microsoft.Compute \
  --output json
```

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Production VM down affecting users | Critical | Immediate Azure support ticket |
| Data loss or corruption | Critical | Immediate support + backup review |
| Security breach indicator | Critical | Immediate support + security review |
| Persistent provisioning failures | High | Support ticket with Activity Log |
| Quota or capacity issues | Medium | Quota increase request via portal |
| Performance issues | Medium | Performance analysis + support |
| Feature clarification | Low | Azure forums or documentation |