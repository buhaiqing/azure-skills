---
name: azure-dns-ops
description: >-
  Use when operating Azure DNS Zones and DNS Records via Azure CLI or Azure SDK;
  user mentions "DNS Zone", "DNS record", "name resolution", "domain", "private DNS", or "DNS delegation".
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials (Service Principal),
  network access to Azure endpoints.
metadata:
  author: azure
  version: "1.0.0"
  last_updated: "2026-07-11"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_TENANT_ID
    - AZURE_CLIENT_ID
    - AZURE_CLIENT_SECRET
---

# Azure DNS Operations Skill

## Overview

Azure DNS provides domain name resolution for Azure resources and external domains via public and private DNS zones. This skill is the operational runbook for DNS Zones and Record Sets: **Pre-flight → Execute → Validate → Recover**.

## Trigger & Scope

### SHOULD Use When
- User mentions "DNS Zone", "DNS record", "domain name", "name resolution", "private DNS", or "DNS delegation"
- Task involves CRUD on **DNS Zones** (public or private) or **Record Sets** (A, AAAA, CNAME, MX, NS, SRV, TXT, SOA, PTR, ALIAS)
- Task involves DNS delegation (NS records), zone import/export, or DNS resolution troubleshooting
- DNS foundation is required before domain-verified Azure services (App Service, Front Door, CDN, Key Vault)

### SHOULD NOT Use When
- DNS-based global traffic routing → delegate to: `azure-trafficmanager-ops`
- Global L7/CDN/SSL → delegate to: `azure-frontdoor-ops`
- Application Gateway custom domain → delegate to: `azure-appgateway-ops`
- Private DNS zone linked to VNet → delegate to: `azure-vnet-ops` (VNet integration); DNS record CRUD stays here
- Certificate validation / domain verification → delegate to: `azure-keyvault-ops`
- Billing only → delegate to: `azure-cost-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; reuse |
| `{{user.zone_name}}` | User input | DNS zone name (e.g., example.com); ask once |
| `{{user.record_set_name}}` | User input | Record set relative name (@ for apex); ask once |
| `{{user.record_type}}` | User input | A, AAAA, CNAME, MX, NS, SRV, TXT, PTR, SOA |
| `{{user.zone_file_path}}` | User input | Path to zone import/export file; ask once |
| `{{output.zone_id}}` | Last API response | Parse: `.id` from Azure CLI output |
| `{{output.record_set_id}}` | Last API response | Parse: `.id` from record set output |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**. Use Azure CLI first. If CLI fails after up to 3 retries with backoff, use Azure SDK for Python fallback. Public DNS zone create is near-instant; zone delete is an LRO — poll every 10 seconds for up to 10 minutes. Private DNS zone operations (create/update/delete) are LROs. See [Integration Setup](references/integration.md) for SDK client setup and RBAC.

### Operation: Create DNS Zone

#### Pre-flight
CLI available → `az --version`; Credentials → `az account show`; Subscription → `az account list`; Resource Group → `az group show`; Zone name format → validate FQDN (no trailing dot); Private DNS → verify VNet exists.

#### Execute
- CLI primary: `az network dns zone create --name "{{user.zone_name}}" --resource-group "{{user.resource_group}}" --output json`
- CLI private: `az network private-dns zone create --name "{{user.zone_name}}" --resource-group "{{user.resource_group}}" --output json`
- SDK fallback: `DnsManagementClient.zones.create_or_update(...)` / `PrivateDnsManagementClient` for private zones

#### Validate
Show zone (confirm `provisioningState == Succeeded`); capture `{{output.zone_id}}`; list initial NS records.

#### Recover
See [Troubleshooting](references/troubleshooting.md) for full error table. Key: ZoneAlreadyExists / InvalidDomainNameFormat / AuthorizationFailed → HALT; 429/5xx → retry 3x.

### Operation: Create or Update Record Set

#### Pre-flight
Zone exists → `az network dns zone show`; Record type valid (A/AAAA/CNAME/MX/NS/SRV/TXT/SOA/PTR); TTL ≥ 0; CNAME apex conflict check (RFC 1034); ALIAS target resource ID valid.

#### Execute
- CLI primary: `az network dns record-set <type> create|add-record|update|remove --resource-group "{{user.resource_group}}" --zone-name "{{user.zone_name}}" --record-set-name "{{user.record_set_name}}" --output json`
- SDK fallback: `DnsManagementClient.record_sets.create_or_update(...)` or `record_sets.update(...)`

#### Validate
Show record set (confirm TTL, records, metadata); capture `{{output.record_set_id}}`.

#### Recover
RecordSetAlreadyExists → use update; CnameApexConflict / InvalidRecordValue → HALT; 429/5xx → retry 3x.

### Operation: Delete Record Set

**Safety Gate**: MUST obtain explicit user confirmation before record set deletion. Show current record values, TTL, and warn about DNS resolution impact. User must type exact record set name and type.

### Operation: Delete DNS Zone

**Safety Gate**: MUST obtain explicit user confirmation before zone deletion. Show zone NS records, current record sets count, and warn that all records and delegation will be removed. User must type exact zone name.

### Operation: Import / Export Zone File

- CLI export: `az network dns zone export --name "{{user.zone_name}}" -g "{{user.resource_group}}" > zonefile.json`
- CLI import: `az network dns zone import --name "{{user.zone_name}}" -g "{{user.resource_group}}" --file-name "{{user.zone_file_path}}" --output json`

### Operation: Show / List

- CLI: `az network dns zone show --name "{{user.zone_name}}" -g "{{user.resource_group}}" --output json`
- CLI: `az network dns zone list --output json` (all zones in subscription)
- CLI: `az network dns record-set list --zone-name "{{user.zone_name}}" -g "{{user.resource_group}}" --output json`
- SDK: `DnsManagementClient.zones.get(...)`, `zones.list_by_resource_group(...)`, `record_sets.list_by_dns_zone(...)`

## Quality Gate

This skill participates in the **Generator-Critic-Loop (GCL)** adversarial quality gate. See `AGENTS.md §3–§8`.

| Parameter | Value |
|-----------|-------|
| GCL | **required** — DNS zone deletion breaks name resolution in production |
| max_iterations | 2 |
| Rubric | [references/rubric.md](references/rubric.md) |
| Prompt templates | [references/prompt-templates.md](references/prompt-templates.md) |

### GCL Trigger Conditions
- DELETE zone (`az network dns zone delete`) → **required**; DNS delegation loss warning + Safety=0 → ABORT
- DELETE record set → **required**; resolution impact warning + exact-name confirmation
- IMPORT zone file → **recommended**; idempotency check for bulk operations
- CREATE zone / CREATE or UPDATE record set / SHOW / LIST / EXPORT → optional

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## See Also

- See `references/core-concepts.md` for Azure DNS documentation links

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
