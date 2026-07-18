---
name: azure-eventgrid-ops
description: >-
  Use when operating or diagnosing Azure Event Grid resources. User mentions
  Event Grid, event grid topic, system topic, domain, event subscription,
  CloudEvents, dead-letter destination, retry policy, advanced filter,
  subject filter, event delivery, webhook endpoint, or Event Grid quotas
  and validation errors.
license: MIT
compatibility: >-
  Azure CLI 2.0+, Azure SDK for Python (3.10+), valid Azure credentials,
  network access to Azure management endpoints.
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

# Azure Event Grid Operations Skill

## Overview

Azure Event Grid provides managed event routing with publish-subscribe semantics across Azure services. This skill handles Topic, System Topic, Domain, Domain Topic, and Event Subscription CRUD, filter design, retry policy, dead-lettering, and delivery diagnostics. Keep this file concise; load reference files for commands, SDK patterns, RCA rules, and detailed scenarios.

## Trigger & Scope

### SHOULD Use When
- User mentions Event Grid, event grid topic, system topic, domain, event subscription, CloudEvents, or webhook/HTTP endpoint delivery.
- Task involves topic/domain/system-topic create/show/list/update/delete, event subscription CRUD, filter authoring (subject begins-with / event type / advanced filters), retry policy, or dead-letter destination.
- User asks for delivery diagnostics: failed deliveries, dead-letter inspection, validation handshake errors, quota errors.

### SHOULD NOT Use When
- Billing/cost only → delegate to `azure-cost-ops`.
- Cross-product audit, RBAC, locks, policy, or Activity Log-only analysis → delegate to `azure-audit-ops`.
- Generic metrics/log query authoring → delegate to `azure-monitor-ops`.
- Azure Function event trigger setup → delegate to `azure-function-ops`.
- Service Bus queue/topic for guaranteed delivery semantics → delegate to `azure-servicebus-ops`.
- Event Hubs high-throughput streaming → delegate to `azure-eventhub-ops`.
- Storage Queue as an event handler → delegate to `azure-queue-storage-ops`.
- VNet/Private Link deep dive not specific to Event Grid → provide entry diagnostics, then escalate to network owner.

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AZURE_SUBSCRIPTION_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_TENANT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AZURE_CLIENT_SECRET}}` | Runtime env | NEVER ask user; fail if unset |
| `{{user.resource_group}}` | User input | Ask once; required for resource operations |
| `{{user.location}}` | User input | Azure Location, e.g. `eastus`; validate before create |
| `{{user.topic_name}}` | User input | Event Grid custom topic name; ask once |
| `{{user.system_topic_name}}` | User input | System topic name (tied to Azure source resource) |
| `{{user.domain_name}}` | User input | Event Grid domain name |
| `{{user.domain_topic_name}}` | User input | Domain topic name within a domain |
| `{{user.event_subscription_name}}` | User input | Event subscription name; ask once |
| `{{user.endpoint_url}}` | User input | Webhook or HTTP endpoint URL for event delivery |
| `{{user.subject_begins_with}}` | User input | Subject filter prefix (e.g. `containers/`); leave empty for wildcard |
| `{{user.included_event_types}}` | User input | Comma-separated event types (e.g. `Microsoft.Storage.BlobCreated`); empty = all |
| `{{user.max_delivery_attempts}}` | User input | Retry policy max attempts; default 30, range 1-30 |
| `{{user.event_ttl_minutes}}` | User input | Event time-to-live in minutes; default 1440 (24h), range 1-1440 |
| `{{user.storage_account_name}}` / `{{user.dead_letter_container}}` | User input | Storage account + blob container (system-topic source / dead-letter destination) |
| `{{user.analysis_window}}` | User input | Default `PT1H`; use `PT6H`/`P1D` for incidents |
| `{{user.private_endpoint_name}}` / `{{user.vnet_name}}` / `{{user.subnet_name}}` | User input | Private endpoint + VNet + subnet names for private link; ask once each |
| `{{output.topic_id}}` | CLI/SDK output | Parse from `.id` |
| `{{output.event_subscription_id}}` | CLI/SDK output | Parse from `.id` |
| `{{output.delivery_attributes}}` | SDK output | `get_delivery_attributes` returns static/dynamic HTTP header attribute mappings (`DeliveryAttributeMapping[]`) |

## JSON Paths

```yaml
TOPIC_ID: id
TOPIC_STATE: properties.provisioningState
TOPIC_ENDPOINT: properties.endpoint
TOPIC_INPUT_SCHEMA: properties.inputSchema
EVENT_SUBSCRIPTION_ID: id
EVENT_SUBSCRIPTION_STATE: properties.provisioningState
EVENT_SUBSCRIPTION_ENDPOINT: properties.destination.endpointUrl
EVENT_SUBSCRIPTION_FILTER_SUBJECT: properties.filter.subjectBeginsWith
EVENT_SUBSCRIPTION_FILTER_TYPES: properties.filter.includedEventTypes
DEAD_LETTER_ENDPOINT: properties.deadLetterWithResourceIdentity.destination.endpointUrl
PROVISIONING_STATE_SUCCEEDED: "Succeeded"
```

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover → Report**.

| Phase | Required Actions |
|-------|------------------|
| Pre-flight | Verify CLI, credentials, subscription, Resource Group, Location, provider `Microsoft.EventGrid`, RBAC, and target resource state. |
| Execute | Use Azure CLI primary. Retry transient CLI failures up to 3x with backoff before SDK fallback. |
| Validate | Confirm provisioning/state with `--output json`; poll LRO every 30s, max 30m unless reference says otherwise. |
| Recover | Apply HALT-vs-retry matrix; never guess fields or retry destructive actions blindly. |
| Report | Return evidence, confidence, safe next actions, and actions requiring confirmation. |

## Operation Map

| Intent | Primary CLI | Reference |
|--------|-------------|-----------|
| Topic / System Topic CRUD | `az eventgrid topic` / `az eventgrid system-topic` | [integration.md](references/integration.md) |
| Domain / Domain Topic CRUD | `az eventgrid domain` / `az eventgrid domain-topic` | [integration.md](references/integration.md) |
| Event Subscription CRUD | `az eventgrid event-subscription` | [integration.md](references/integration.md) |
| Topic keys & event types | `az eventgrid topic show` / `key list` / `list-event-types` | [integration.md](references/integration.md) |
| Delivery diagnostics | `get_delivery_attributes` SDK / dead-letter inspection | [troubleshooting.md](references/troubleshooting.md) |

## Safety Gates

Require explicit human confirmation with exact resource name and Resource Group before:
- delete topic, delete system topic, delete domain, or delete domain topic;
- delete the Azure source resource that backs a system topic (system topic is auto-deleted on source deletion — all dependent event subscriptions stop receiving events);
- delete event subscription (impact on handler endpoints — events stop arriving);
- regenerate key on topic or domain;
- reduce retry-policy `max_delivery_attempts` or `event_ttl_minutes` below current production value;
- broaden public network access or disable local auth on topic/domain.

If confirmation is missing or user asks to skip it, HALT and explain the required confirmation.

## Recovery Matrix

| Condition | Agent Action |
|-----------|--------------|
| AuthorizationFailed / AccessDenied | HALT; report required RBAC from [integration.md](references/integration.md) |
| ResourceNotFound | HALT; verify name, Resource Group, subscription |
| InvalidLocation / SKU unavailable | HALT; validate Location and suggest supported options |
| Quota exceeded (`ResourceQuotaExceeded`) | HALT; request quota increase or choose another Location |
| Throttling / 429 | Backoff and retry up to 3x |
| 5xx / transient network | Retry up to 3x, then HALT with correlation ID |
| Endpoint `ValidationFailed` (handshake) | HALT; instruct handler to echo `validationCode` in response |
| Destructive action without confirmation | HALT; require explicit confirmation |

## Quality Gate

GCL is required for destructive operations (delete topic, delete system topic, delete domain, delete event subscription, regenerate key). Use [rubric.md](references/rubric.md) and [prompt-templates.md](references/prompt-templates.md). Rubric dimensions: correctness, safety, idempotency, traceability, spec compliance. Safety score `0` aborts immediately. max_iterations: 2. Persist traces to `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` with secrets masked as `***`.

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [Integration and Commands](references/integration.md)
- [Troubleshooting and RCA](references/troubleshooting.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)
