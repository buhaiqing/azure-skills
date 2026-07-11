# Troubleshooting — Azure DNS

## Error Decision Table

| Symptom / Error | Likely Cause | Action |
|-----------------|--------------|--------|
| `ZoneAlreadyExists` | DNS zone name already exists in Azure DNS (globally unique) | HALT; use different zone name |
| `InvalidDomainNameFormat` | Zone name has trailing dot or invalid characters | HALT; correct domain format (no trailing dot in `--name`) |
| `RecordSetAlreadyExists` | Record set with same name/type already exists | Use update or `create_or_update` instead of create |
| `CnameApexConflict` | CNAME coexists with other records at the same name (RFC 1034) | HALT; explain RFC conflict; suggest ALIAS or remove other records |
| `InvalidRecordValue` | Record value format incorrect (e.g., bad IP, invalid FQDN) | HALT; correct record value |
| `AuthorizationFailed` | Missing DNS Zone Contributor or equivalent role | HALT; request RBAC fix |
| `ResourceNotFound` | Wrong zone name, record set name, or Resource Group | Verify names and subscription |
| `QuotaExceeded` | Max zones or record sets per subscription reached | HALT; request quota increase |
| `AnotherOperationInProgress` | Zone-level LRO still running (zone delete) | Wait and poll; do not start conflicting operation |
| `TooManyRequests` / 429 | Azure throttling | Backoff and retry up to 3 times |
| 5xx | Azure control-plane transient issue | Retry up to 3 times, then HALT |

## DNS Resolution Troubleshooting

### Issue: Domain not resolving after zone creation

**Diagnosis Steps**:
1. Verify zone exists: `az network dns zone show --name "{{user.zone_name}}" -g "{{user.resource_group}}" --output json`
2. Check NS records: `az network dns record-set show --name "@" --zone-name "{{user.zone_name}}" -g "{{user.resource_group}}" --record-type NS --output json`
3. Verify delegation: `dig NS {{user.zone_name}}` — should return Azure name servers
4. Check at registrar: NS records must match Azure-assigned name servers
5. Wait for propagation: DNS changes can take 24-48 hours globally

### Issue: Record not resolving after update

**Diagnosis Steps**:
1. Verify record exists: `az network dns record-set show --name "{{user.record_set_name}}" --zone-name "{{user.zone_name}}" -g "{{user.resource_group}}" --record-type "{{user.record_type}}" --output json`
2. Check TTL: Lower TTL means faster propagation
3. Clear local DNS cache: `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder` (macOS) or `ipconfig /flushdns` (Windows)
4. Test from different resolvers: `dig @8.8.8.8 "{{user.record_set_name}}.{{user.zone_name}}"`

### Issue: Private DNS not resolving

**Diagnosis Steps**:
1. Verify private zone exists: `az network private-dns zone show --name "{{user.zone_name}}" -g "{{user.resource_group}}" --output json`
2. Check VNet links: `az network private-dns link vnet list --zone-name "{{user.zone_name}}" -g "{{user.resource_group}}" --output json`
3. Verify VNet link status: should be `Completed`
4. Check auto-registration: If enabled, VMs in linked VNet auto-register A records
5. Verify VM is in linked VNet: `az vm show --name "{{user.vm_name}}" -g "{{user.resource_group}}" --query "networkProfile" --output json`

### Issue: Delegation errors

**Diagnosis Steps**:
1. Verify NS records at registrar match Azure's name servers
2. Check for missing glue records (if using custom name servers)
3. Verify DS/DNSSEC records (if DNSSEC is enabled)
4. Test: `dig +trace "{{user.zone_name}}"` to follow delegation chain

### Issue: CNAME + other records conflict

**Diagnosis Steps**:
1. List all records at the name: `az network dns record-set list --zone-name "{{user.zone_name}}" -g "{{user.resource_group}}" --query "[?name=='{{user.record_set_name}}']" --output json`
2. If CNAME coexists with A/AAAA/MX/TXT/NS/SRV → RFC violation
3. Resolution: Use ALIAS record instead of CNAME, or remove conflicting records

### Issue: Alias record not resolving

**Diagnosis Steps**:
1. Verify target resource exists and is running
2. Check target resource type: TM, Front Door, CDN, public IP, App Service
3. Verify RBAC: Generator must have Reader on target resource
4. Check for target resource IP changes (alias records update automatically)

## DNS Propagation Timing

| Change Type | Propagation Time | Notes |
|-------------|-----------------|-------|
| New zone delegation | 24-48 hours | Global DNS propagation |
| Record TTL change | TTL value + cache time | Varies by resolver |
| Record value change | Up to TTL value | Client DNS cache dependent |
| NS record change | 24-48 hours | Registrar and TLD propagation |
| Private DNS change | Near-instant | Within linked VNet only |

## Dependency Discovery Before Delete

Before DNS zone deletion, see [Validation Commands in core-concepts.md](core-concepts.md#validation-commands) for zone and record set inspection commands.

Before record set deletion, see [Validation Commands in core-concepts.md](core-concepts.md#validation-commands) for record set inspection commands.

## Polling Strategy

Zone delete is an LRO. Poll every 10 seconds for up to 10 minutes using the `az network dns zone show` command (see [Validation Commands in core-concepts.md](core-concepts.md#validation-commands)). Expected terminal state: `Succeeded` (for zone create/update — near-instant). For delete, `ResourceNotFound` confirms completion.

## Activity Log

```bash
az monitor activity-log list --resource-group "{{user.resource_group}}" --status Failed --max-events 20 --output json
```

Use Activity Log to identify policy denial, RBAC denial, quota, and platform failures.

## Safety Handling

- Never bypass confirmation for zone or record set deletion.
- Never delete a zone that is actively delegating a production domain.
- Never create a CNAME record that conflicts with existing records at the same name.
- Never print `{{env.AZURE_CLIENT_SECRET}}` or credential values in traces.
- For zone import: always review the import file for unintended record overwrites.
