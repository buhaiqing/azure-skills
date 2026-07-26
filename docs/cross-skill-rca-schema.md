# Cross-Skill RCA Schema

> Standard schema for cross-service root cause analysis across Azure skills.
> Entry point: `azure-monitor-ops` (user reports issue) → diagnostic path → root cause.

## RCA Chain Schema

Every cross-skill RCA follows this structure:

```yaml
rca_chain:
  entry_point: azure-monitor-ops    # where the user reports the issue
  symptom: <string>                  # what the user observed
  diagnostic_paths:                  # ordered list of diagnostic steps
    - skill: <skill-name>
      check: <what to check>
      command: <az command to run>
      pass_criteria: <what "healthy" looks like>
      fail_action: <what to do on failure>
  root_cause: <skill-name>          # diagnosed root cause
  recommendation: <string>          # what to do next
```

## Standard Diagnostic Paths

### Web Application Latency

```
entry_point: azure-monitor-ops (user: "app is slow")
diagnostic_paths:
  - skill: azure-appgateway-ops
    check: Backend health and latency
    command: az network application-gateway show-backend-health --name <gw> --resource-group <rg>
    pass_criteria: All backend servers Healthy, latency < 500ms
    fail_action: Check backend pool configuration

  - skill: azure-vm-ops
    check: VM CPU/Memory/Disk IO
    command: az monitor metrics list --resource <vm_id> --metric "Percentage CPU"
    pass_criteria: CPU < 80%, Available Memory > 1GB
    fail_action: Check for resource contention, recommend resize

  - skill: azure-sqldb-ops (or azure-postgres-ops)
    check: Database DTU/CPU/Query performance
    command: az monitor metrics list --resource <db_id> --metric "dtu_consumption_percent"
    pass_criteria: DTU < 80%, no slow queries in query store
    fail_action: Check query performance, recommend index tuning

  - skill: azure-redis-ops (if applicable)
    check: Cache hit ratio and latency
    command: az monitor metrics list --resource <redis_id> --metric "cacheHitRate"
    pass_criteria: Cache hit rate > 80%, server load < 50%
    fail_action: Check eviction rate, recommend scaling
```

### API Access Failure (502/503)

```
entry_point: azure-monitor-ops (user: "API returns 502")
diagnostic_paths:
  - skill: azure-apim-ops
    check: Backend health, subscription status
    command: az apim api show --service <apim> --api-id <api>
    pass_criteria: API is active, subscription not expired
    fail_action: Check subscription keys, check backend URL

  - skill: azure-appgateway-ops
    check: WAF rules, backend pool health
    command: az network application-gateway waf-policy show --name <waf> --resource-group <rg>
    pass_criteria: WAF not blocking, backend healthy
    fail_action: Check WAF logs for blocked requests

  - skill: azure-aks-ops (if Kubernetes backend)
    check: Pod status, service endpoints
    command: kubectl get pods --namespace <ns>
    pass_criteria: All pods Running, ready 1/1
    fail_action: Check pod logs, describe failing pods
```

### Database Performance Degradation

```
entry_point: azure-monitor-ops (user: "database queries are slow")
diagnostic_paths:
  - skill: azure-sqldb-ops (or azure-postgres-ops, azure-cosmos-ops)
    check: DTU/RU consumption, query store, wait stats
    command: az monitor metrics list --resource <db_id> --metric "dtu_consumption_percent"
    pass_criteria: DTU < 80%, no blocking queries
    fail_action: Check top resource-consuming queries

  - skill: azure-vm-ops (if application VM)
    check: Application-to-database connection pool
    command: az vm run-command invoke --command-id RunShellScript --scripts "ss -tlnp | grep 1433"
    pass_criteria: Connection pool adequate, no timeouts
    fail_action: Check application-side connection pooling

  - skill: azure-monitor-ops
    check: Log Analytics for correlated errors
    command: az monitor log-analytics query --workspace <ws> --query "AppExceptions | where TimeGenerated > ago(1h)"
    pass_criteria: No database-related exceptions
    fail_action: Extract exception details for root cause
```

## Cost Anomaly Diagnostic Path

```
entry_point: azure-cost-ops (user: "cost spiked")
diagnostic_paths:
  - skill: azure-cost-ops
    check: Cost breakdown by service/resource
    command: az costmanagement query --scope ... --timeframe MonthToDate
    pass_criteria: Cost change explained by known scaling events
    fail_action: Identify top-cost-increased service

  - skill: azure-monitor-ops
    check: Activity Log for resource creation/modification
    command: az monitor activity-log list --start-time <30d_ago>
    pass_criteria: All cost-increasing changes are authorized
    fail_action: Flag unauthorized resource creation

  - skill: (affected service skill)
    check: Resource scaling/utilization changes
    command: az monitor metrics list --resource <id> --metric <relevant_metric>
    pass_criteria: Resource scaling correlates with cost change
    fail_action: Investigate billing tier changes
```

## RCA Report Format

When a cross-skill RCA completes, output a standardized report:

```json
{
  "rca_id": "<uuid>",
  "timestamp": "<ISO8601>",
  "symptom": "<user-reported issue>",
  "diagnostic_path_taken": ["skill1", "skill2", "..."],
  "findings": [
    {
      "skill": "<skill-name>",
      "resource": "<resource_id>",
      "status": "HEALTHY | DEGRADED | FAILED",
      "metrics": {"key": "value"},
      "details": "<description>"
    }
  ],
  "root_cause": {
    "skill": "<skill-name>",
    "resource": "<resource_id>",
    "reason": "<analysis>",
    "confidence": "HIGH | MEDIUM | LOW"
  },
  "recommendation": "<action to resolve>",
  "escalation_required": true|false
}
```

## Escalation Rules

| Condition | Action |
|-----------|--------|
| Root cause confidence LOW | Escalate to human with all findings |
| Multiple skills show FAILED status | Escalate as potential platform issue |
| Safe healing action available | Execute via auto_feedback_loop.py |
| Destructive healing required | Escalate to human for confirmation |
| Cost anomaly + unauthorized activity | Escalate to security team |

## Additional Diagnostic Paths

### Container Image Pull Failure

```
entry_point: azure-monitor-ops (user: "container fails to start / ImagePullBackOff")
diagnostic_paths:
  - skill: azure-acr-ops
    check: Image exists in registry, authentication
    command: az acr repository show-tags --name <acr> --repository <repo>
    pass_criteria: Image tag exists, ACR healthy
    fail_action: Check image push logs, verify ACR permissions

  - skill: azure-aks-ops
    check: ACR pull secret, pod image pull policy
    command: kubectl get secret -n <ns> && kubectl describe pod <pod>
    pass_criteria: Pull secret valid, image reference correct
    fail_action: Regenerate ACR pull secret, fix image tag
```

### Global Traffic / DNS Resolution Issue

```
entry_point: azure-monitor-ops (user: "users cannot access app from certain regions")
diagnostic_paths:
  - skill: azure-frontdoor-ops
    check: Origin health, routing rules, WAF
    command: az afd endpoint list --profile <profile>
    pass_criteria: All endpoints healthy, routing correct
    fail_action: Check origin configuration, WAF rules

  - skill: azure-loadbalancer-ops
    check: Backend pool health, probe status
    command: az network lb show --name <lb> --resource-group <rg>
    pass_criteria: All backends healthy, probes succeeding
    fail_action: Check backend VMs, NSG rules for probe traffic

  - skill: azure-monitor-ops
    check: DNS resolution, global latency metrics
    command: az network dns zone show --name <zone> --resource-group <rg>
    pass_criteria: DNS records correct, no propagation issues
    fail_action: Check DNS TTL, verify record updates
```

### Messaging / Event Processing Lag

```
entry_point: azure-monitor-ops (user: "messages not being processed / lag detected")
diagnostic_paths:
  - skill: azure-servicebus-ops
    check: Queue/topic depth, dead-letter queue, throttling
    command: az servicebus queue show --name <queue> --namespace <ns> --resource-group <rg>
    pass_criteria: Queue depth stable, DLQ minimal, no throttling
    fail_action: Check consumer health, scale consumers

  - skill: azure-eventhub-ops
    check: Partition lag, consumer group offsets, capture status
    command: az eventhubs eventhub show --name <hub> --namespace <ns> --resource-group <rg>
    pass_criteria: Lag stable, offsets advancing, capture active
    fail_action: Check consumer application, scale partitions

  - skill: azure-monitor-ops
    check: Consumer application metrics, error logs
    command: az monitor metrics list --resource <app_id> --metric "Requests"
    pass_criteria: Consumer processing, no error spikes
    fail_action: Check consumer app logs, restart consumers
```

### Secret / Certificate Access Failure

```
entry_point: azure-monitor-ops (user: "application fails to access secrets / auth errors")
diagnostic_paths:
  - skill: azure-keyvault-ops
    check: Vault access policies, RBAC, firewall, certificate expiry
    command: az keyvault show --name <vault> --query "properties.accessPolicies"
    pass_criteria: Access policy grants required permissions, certificates valid
    fail_action: Update access policy, check firewall rules, renew certificates

  - skill: azure-vm-ops (if VM-based app)
    check: Managed identity configuration
    command: az vm identity show --name <vm> --resource-group <rg>
    pass_criteria: Managed identity assigned, has KV access
    fail_action: Assign managed identity, grant KV permissions

  - skill: azure-appservice-ops (if App Service app)
    check: App managed identity, Key Vault references in app settings
    command: az webapp identity show --name <app> --resource-group <rg>
    pass_criteria: Identity assigned, KV references resolve
    fail_action: Enable managed identity, fix KV reference syntax
```

### App Service Performance Issue

```
entry_point: azure-monitor-ops (user: "web app slow / cold starts / restarts")
diagnostic_paths:
  - skill: azure-appservice-ops
    check: CPU/Memory, instance count, cold start metrics
    command: az webapp show --name <app> --resource-group <rg> --query "siteConfig"
    pass_criteria: Adequate tier, always-on enabled (if needed)
    fail_action: Scale up tier, enable always-on, check deployment slots

  - skill: azure-monitor-ops
    check: Response time distribution, error rate
    command: az monitor metrics list --resource <app_id> --metric "HttpResponseTime"
    pass_criteria: P95 < 1s, error rate < 1%
    fail_action: Check application logs, dependency latency

  - skill: azure-sqldb-ops (if database-backed)
    check: Database connection time, DTU
    command: az monitor metrics list --resource <db_id> --metric "dtu_consumption_percent"
    pass_criteria: DTU < 80%, connection time < 100ms
    fail_action: Check connection pooling, scale database
```

## Skill Coverage Matrix

| Diagnostic Path | Skills Covered |
|-----------------|----------------|
| Web Application Latency | appgateway, vm, sqldb/postgres, redis |
| API Access Failure | apim, appgateway, aks |
| Database Performance | sqldb/postgres/cosmos, vm, monitor |
| Cost Anomaly | cost, monitor, *(service) |
| Container Image Pull | acr, aks |
| Global Traffic/DNS | frontdoor, loadbalancer, monitor |
| Messaging/Event Lag | servicebus, eventhub, monitor |
| Secret/Cert Access | keyvault, vm, appservice |
| App Service Performance | appservice, monitor, sqldb |