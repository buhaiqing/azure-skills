# L4 Live Canary Report

> Generated: 2026-07-31T16:42:22.634445+00:00

> Mode: `dry_run`

## Summary

| Metric | Value |
|--------|-------|
| Total | 8 |
| Passed | 8 |
| Failed | 0 |
| Skipped | 0 |

## Per skill

| Skill | Operation | Tier | Status | Detail |
|-------|-----------|------|--------|--------|
| azure-vm-ops | vm_show | R0 | dry_run_ok | requires env: AZURE_RESOURCE_GROUP |
| azure-aks-ops | aks_list | R0 | dry_run_ok | requires env: AZURE_RESOURCE_GROUP |
| azure-blobstorage-ops | account_list | R0 | dry_run_ok | requires env: AZURE_RESOURCE_GROUP |
| azure-appgateway-ops | ag_list | R0 | dry_run_ok | requires env: AZURE_RESOURCE_GROUP |
| azure-loadbalancer-ops | lb_list | R0 | dry_run_ok | requires env: AZURE_RESOURCE_GROUP |
| azure-frontdoor-ops | afd_list | R0 | dry_run_ok | requires env: AZURE_RESOURCE_GROUP |
| azure-vnet-ops | vnet_list | R0 | dry_run_ok | requires env: AZURE_RESOURCE_GROUP |
| azure-keyvault-ops | kv_list | R0 | dry_run_ok | requires env: AZURE_RESOURCE_GROUP |

> Dry-run / non-live: set `AZURE_RESOURCE_GROUP` and run `python3 scripts/live_canary.py --env=live` for production evidence.
