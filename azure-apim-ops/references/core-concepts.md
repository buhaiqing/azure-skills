# Azure API Management Core Concepts

## What is Azure API Management

- **Purpose**: Managed API gateway for publishing, securing, transforming, monitoring, and monetizing HTTP APIs
- **Category**: Networking / Application Delivery / API Gateway
- **Portal**: https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.ApiManagement%2Fservice
- **Docs**: https://learn.microsoft.com/azure/api-management/
- **Pricing**: https://azure.microsoft.com/pricing/details/api-management/

## Resource Hierarchy

```
API Management Service (Microsoft.ApiManagement/service)
├── APIs (Microsoft.ApiManagement/service/apis)
│   ├── Operations (per-API endpoints)
│   ├── Revisions (immutable snapshots)
│   ├── Releases (pinned revision)
│   ├── Policies (XML, scoped to API)
│   └── Schemas (OpenAPI / GraphQL / WSDL)
├── Products (Microsoft.ApiManagement/service/products)
│   ├── APIs (associated APIs)
│   ├── Subscriptions (developer keys)
│   ├── Policies (XML, scoped to Product)
│   └── Groups (visibility)
├── Subscriptions (Microsoft.ApiManagement/service/subscriptions)
├── Policies (global: PolicyIdName.policy)
├── Named Values (key-value store, can be secret)
├── Backends (HTTP backend pool / circuit breaker)
├── Groups (built-in: administrators, developers, guests; custom)
└── Developer Portal (auto-generated static site)
```

## Resource ID Format

```
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.ApiManagement/service/{apim-name}
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.ApiManagement/service/{apim-name}/apis/{api-id}
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.ApiManagement/service/{apim-name}/products/{product-id}
/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.ApiManagement/service/{apim-name}/subscriptions/{sid}
```

## SKU Comparison

| SKU | Use Case | Capacity (units) | VNet | Multi-region | SLA |
|-----|----------|------------------|------|--------------|-----|
| **Consumption** | Serverless, low traffic, pay-per-call | Auto (serverless) | ❌ | ❌ | None |
| **Developer** | Dev/test, single region | 1 | ❌ | ❌ | None |
| **Basic** | Entry-level prod | 1–2 | ❌ | ❌ | 99.95% |
| **Standard** | Mid-tier prod | 1–4 | ❌ | ✅ (up to 10) | 99.95% |
| **Premium** | High-scale, mission-critical | 1–11 | ✅ (Internal/External) | ✅ (up to 11) | 99.99% |
| **Isolated** | Dedicated, compliance | 1–11 | ✅ | ❌ | 99.99% |

> **SKU name mapping**: Azure CLI `--sku-name` accepts `{Basic, Consumption, Developer, Isolated, Premium, Standard}`. Azure SDK `SkuType` enum additionally includes `BasicV2` and `StandardV2` (REST API only). Use lowercase enum value in CLI; PascalCase enum value in SDK.

## API Types

| Type | Description |
|------|-------------|
| **HTTP** | REST API with HTTP backend (`serviceUrl` + `path`) |
| **SOAP** | WSDL pass-through / SOAP-to-REST |
| **WebSocket** | Stateful bidirectional |
| **GraphQL** | Schema + resolvers (`/graphql` API type) |

## Auth & Subscription

| Mechanism | How | Use Case |
|-----------|-----|----------|
| **Subscription key** | Header `Ocp-Apim-Subscription-Key` or query `?subscription-key=` | Developer-portal products |
| **JWT** | Validate JWT in `<validate-jwt>` policy | OAuth2/OIDC backends |
| **Client cert** | `enable-client-certificate=true` on APIM | mTLS |
| **Managed identity** | APIM → backend auth (no key in gateway URL) | AAD-protected backends |

## Policies (XML)

Policies are XML documents applied at scopes:
- **Global** (`policyId="policy"`) — applies to all APIs
- **Product** — applies to APIs in the product
- **API** (`policyId="policy"`) — applies to all operations of an API
- **Operation** — applies to one operation

```xml
<policies>
  <inbound>
    <base />
    <rate-limit calls="100" renewal-period="60" />
    <set-header name="X-Trace-Id" exists-action="skip">
      <value>@(context.RequestId)</value>
    </set-header>
  </inbound>
  <backend>
    <base />
  </backend>
  <outbound>
    <base />
    <set-body>@(context.Response.Body.As<string>(preserveContent: true))</set-body>
  </outbound>
  <on-error>
    <base />
  </on-error>
</policies>
```

`format` is `xml` or `rawxml` (single root element) — `xml` is preferred.

## Versions & Revisions

- **Revision**: Immutable snapshot of an API; add suffix `;rev=N` to path
- **Version**: User-facing label (e.g., `v1`, `v2`); add suffix `;v=v1` to path
- **Version Set**: Groups versions and revisions of an API; required for versioning
- **Release**: Pins a revision as "Current" so it serves traffic without `;rev=N` suffix

## Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| API Management services per subscription | 200 (varies by region) | Yes (Azure support) |
| APIs per service | 500 (Developer) / unlimited (Standard+) | Yes |
| Products per service | 500 (Developer) / unlimited | Yes |
| Subscriptions per product | 1000 | Yes |

## Lifecycle States

| State | Description |
|-------|-------------|
| **Creating** | Service instance provisioning (LRO) |
| **Activating** | Transitioning to Active |
| **Active** | Operational; serving traffic |
| **Updating** | Applying configuration changes |
| **Stopping** / **Stopped** | Gateway disabled; can be re-enabled |
| **Starting** | Transitioning to Active |
| **Deleting** | Removal in progress (LRO) |
| **Deleted** | Resource gone (but recoverable via `az apim deletedservice`) |
| **Failed** | Provisioning or update failed |

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| Resource Group | Yes | (resource provider) |
| Subscription (publisher) | Yes (with publisher_email) | `azure-skill-generator` |
| VNet (internal mode, Premium/Isolated only) | Optional | `azure-network-ops` |
| Application Insights (logging) | Optional | `azure-monitor-ops` |
| Backend service | Optional | depends on type |

## Best Practices

### Security
- Always require subscription key on published APIs (default)
- Validate JWT for backend-issued tokens
- Rotate subscription keys periodically (`regenerate_primary_key`)
- Use `<ip-filter>` to restrict source IPs when possible
- Enable managed identity for APIM → backend auth (no shared secrets)

### Performance
- Use **cache** policy (`<cache-lookup>` / `<cache-store>`) for cacheable GETs
- Configure `<rate-limit>` to protect backends from traffic spikes
- Use `<set-backend-service>` to swap backends without redeploying
- Enable Application Insights for tracing

### Versioning
- Create a **Version Set** before adding revisions
- Use **Current revision** + **Release** to serve traffic without `;rev=` suffix
- Add **deprecation** headers via `<set-header>` when sunsetting a version

### Multi-region (Standard/Premium)
- Add locations via `additional_locations` in SDK or `az apim update`
- Use `<set-backend-service backend-id="..."/>` to route to regional backends
- Monitor each region with `az monitor metrics list`

## Common Patterns

### Pattern 1: Publish a Function API behind APIM
- Steps:
  1. Create Function App + function (`azure-function-ops`)
  2. Create APIM instance (Developer SKU for test)
  3. Import OpenAPI spec via `az apim api import --specification-format OpenApi`
  4. Create a Product, add the API to it
  5. Create a Subscription; obtain primary key (SDK only — `subscription.list_secrets`)
  6. Call API with `Ocp-Apim-Subscription-Key: <primary>`

### Pattern 2: Rate-limited public API
- Steps:
  1. Create APIM (Standard/Premium)
  2. Import API
  3. Create Product with `subscriptions_limit` and `approval_required=true`
  4. Apply product-scoped policy with `<rate-limit calls="1000" renewal-period="3600" />`
  5. Issue subscription keys per developer

### Pattern 3: Backend rewrite + JWT validation
- Steps:
  1. Create APIM with managed identity
  2. Grant APIM identity "Access Reader" on backend (AAD-protected)
  3. Import API; backend URL = AAD app ID URI
  4. Apply API-scoped policy:
     - `<validate-jwt>` for incoming JWT
     - `<authentication-managed-identity>` for backend auth

### Pattern 4: Internal VNet mode (Premium)
- Use case: APIM must not be on public internet
- Steps:
  1. Create VNet + subnet (`azure-network-ops`)
  2. Create APIM with `--virtual-network Internal`
  3. Configure NSG on subnet (allow management + portal traffic)
  4. Test via private endpoint or jumpbox

## Soft-Delete Recovery

APIM supports soft-delete:
- After `az apim delete`, service is retained for **48 hours**
- Recover via `az apim deletedservice show` → `purge` is irreversible
- For hard delete immediately, no CLI flag — must call REST API directly with `ForceDelete=true`