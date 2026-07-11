# Azure Functions Core Concepts

## What is Azure Functions

- **Purpose**: Serverless compute — run event-driven code without managing servers
- **Category**: Compute / Serverless (Function App is built on App Service)
- **Portal**: https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.Web%2Fsites
- **Docs**: https://docs.microsoft.com/azure/azure-functions/
- **Pricing**: https://azure.microsoft.com/pricing/details/functions/

## Primary Resources

| Resource | Description | Resource Type |
|----------|-------------|---------------|
| Function App | Management & execution unit (one or more functions) | Microsoft.Web/sites (kind=functionapp) |
| Hosting Plan | Defines scale/billing: Consumption / Premium / Dedicated | Microsoft.Web/serverfarms |
| Storage Account | Required backend store (Consumption plan) | Microsoft.Storage/storageAccounts |
| Function | Individual code unit with a trigger + bindings | Child of Function App |
| Deployment Slot | Staging environment for swap (Premium/Dedicated) | Microsoft.Web/sites/slots |

## Resource ID Format

```
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Web/sites/{{user.function_app_name}}
```

Hosting plan:
```
/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}/resourceGroups/{{user.resource_group}}/providers/Microsoft.Web/serverfarms/{{user.plan_name}}
```

## Hosting Plans (关键概念)

| Plan | Billing | Scale | Cold Start | Best For |
|------|---------|-------|------------|----------|
| **Consumption** | Per-execution + GB-s | 0 → N (auto) | Yes (after idle) | Bursty / event-driven, low cost |
| **Premium (Elastic)** | Pre-warmed instances + scale | Always-on min → N | Minimal (pre-warmed) | Production, VNet, no cold start |
| **Dedicated (App Service)** | Fixed instance | Manual/auto within plan | No (always running) | Long-running, App Service plan reuse |

**Plan selection rules**:
- Consumption requires a Storage Account (`--storage-account`); Premium/Dedicated reuse an existing plan (`--plan`).
- Premium/Dedicated need a pre-created plan via `az functionapp plan create` (delegate: not covered here as CRUD detail — see Azure docs).

## Triggers & Bindings

A function has exactly one **trigger** (what invokes it) and zero or more **bindings** (input/output data).

| Trigger | Source Service | This skill |
|---------|---------------|-----------|
| HTTP | HTTP request | In-skill |
| Timer | Internal scheduler | In-skill |
| Queue | Storage Queue | Configure binding only; provision queue via `azure-blobstorage-ops` |
| Event Hub | Event Hubs | Configure binding only; provision via Event Hubs skill |
| Service Bus | Service Bus | Configure binding only; provision via Service Bus skill |
| Blob | Storage Blob | Configure binding only; provision via `azure-blobstorage-ops` |

**Scope rule**: This skill configures the function's binding metadata; it does NOT provision the upstream event source. Delegate source creation to the dedicated storage/event service skill.

## Function App Anatomy

| Component | Notes |
|-----------|-------|
| App Settings | Env vars, connection strings, `AzureWebJobsStorage`, `FUNCTIONS_WORKER_RUNTIME` |
| `FUNCTIONS_WORKER_RUNTIME` | Must match `--runtime` (dotnet/node/python/java/powershell) |
| Deployment | Zip push, external Git, or CI/CD connected to the app |
| Keys | Host keys / function keys for HTTP auth (manage via `az functionapp keys`) |

## Naming Constraints

| Resource | Rules |
|----------|-------|
| Function App name | Globally unique DNS label, 3-60 chars, lowercase alphanumeric + hyphen |
| Plan name | 1-40 chars, alphanumeric + hyphen |
| Storage account | 3-24 chars, lowercase alphanumeric (global uniqueness) |

## State Model

| State | Meaning |
|-------|---------|
| Running | App healthy and serving |
| Stopped | App stopped (billing may continue on Dedicated) |
| Failed | Provisioning or runtime error |

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| Resource Group | Yes | core `azure-resource-ops` |
| Storage Account (Consumption) | Yes | `azure-blobstorage-ops` |
| Hosting Plan (Premium/Dedicated) | Yes (if not Consumption) | `azure-appservice-ops` |
| Upstream event source | Per trigger | storage/event service skill |

## Best Practices

- Use Consumption for bursty/low-traffic; Premium for production with VNet & no cold start.
- Keep `FUNCTIONS_WORKER_RUNTIME` consistent with deployed code language.
- Use deployment slots + swap for zero-downtime on Premium/Dedicated.
- Store secrets in App Settings or Key Vault reference, never inline.
