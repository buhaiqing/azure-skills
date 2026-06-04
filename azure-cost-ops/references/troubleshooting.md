# Troubleshooting — azure-cost-ops

> Error codes and diagnostics for Azure Cost Management operations.

## Error Recovery Table

| Error | Probable Cause | Action |
|-------|---------------|--------|
| AuthorizationFailed (403) | Insufficient RBAC — needs Cost Management Reader | HALT; assign `Cost Management Reader` role |
| ProviderNotRegistered | `Microsoft.CostManagement` not registered | `az provider register --namespace Microsoft.CostManagement` |
| InvalidTimeframe | Invalid time range format | Use valid timeframe or YYYY-MM-DD dates |
| SubscriptionNotFound | Wrong subscription ID | HALT; verify subscription ID |
| ScopeNotFound | Invalid scope path | HALT; verify scope: `/subscriptions/{id}` |
| 5xx Internal | Azure server error | Retry 3x with backoff, then HALT |
| BudgetNotFound | Budget name does not exist | `az consumption budget list` to find valid names |
| InvoiceNotFound | Invoice ID invalid or billing account wrong | HALT; verify billing account ID and invoice name |
| 429 Throttling | Rate limit exceeded | Backoff 30s, retry |
| ReservationNotFound | Reservation order/ID invalid | HALT; verify reservation ID |

## Common Issues

### Cost query returns empty rows
- **Check 1**: Subscription has active resources (no resources = no cost)
- **Check 2**: Timeframe is correct — new subscriptions may have no data yet
- **Check 3**: `Microsoft.CostManagement` provider is registered
- **Check 4**: Service Principal has `Cost Management Reader` role

### Budget create fails
- **Check 1**: Budget name must be unique per scope
- **Check 2**: Amount must be a positive number
- **Check 3**: Time period dates are in the future
- **Check 4**: Service Principal has `Cost Management Contributor` role

### Invoice download fails
- **Check 1**: Billing account ID is correct and set in env
- **Check 2**: Invoice is available (not past retention)
- **Check 3**: Service Principal has `Billing Reader` role

### Reservation query empty
- **Check 1**: No reservations purchased for this subscription
- **Check 2**: Reservation is under a different scope (shared/management group)
- **Check 3**: Use `az reservations reservation-order list` for order-level data

## Verification Commands

```bash
# Verify Cost Management provider is registered
az provider show --namespace Microsoft.CostManagement --query "registrationState"

# Test cost query (minimal)
az costmanagement query --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" \
  --dataset-grouping name "ServiceName" type "Dimension" \
  --output json --query "rows[0:3]"

# Test budget list
az consumption budget list --scope "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" --output json

# Verify RBAC
az role assignment list --assignee "{{principal_id}}" \
  --query "[?roleDefinitionName=='Cost Management Reader']"
```

## Rate Limits

| API | Limit | Notes |
|-----|-------|-------|
| Cost Management Query | 100 req/min per scope | Use filters to narrow |
| Consumption Budget | 50 req/min per scope | Create/delete/update |
| Reservation | 30 req/min per subscription | |
| Invoice | 20 req/min per billing account | |