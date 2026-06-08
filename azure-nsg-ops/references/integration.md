# Azure Network Security Group Integration

## Required Environment

Never ask the user to paste secrets. Read credentials only from runtime environment variables.

```bash
export AZURE_SUBSCRIPTION_ID="{{env.AZURE_SUBSCRIPTION_ID}}"
export AZURE_TENANT_ID="{{env.AZURE_TENANT_ID}}"
export AZURE_CLIENT_ID="{{env.AZURE_CLIENT_ID}}"
export AZURE_CLIENT_SECRET="{{env.AZURE_CLIENT_SECRET}}"
```

## RBAC

Minimum recommended role: **Network Contributor** on the target Resource Group or subscription.

Read-only inspection can use **Reader** plus network read permissions, but create/update/delete/associate operations require Network Contributor or equivalent custom permissions for `Microsoft.Network/networkSecurityGroups/*`, `Microsoft.Network/networkInterfaces/*`, and `Microsoft.Network/virtualNetworks/subnets/*`.

## Azure CLI Primary Path

Authenticate and select subscription:

```bash
az login --service-principal \
  --username {{env.AZURE_CLIENT_ID}} \
  --password {{env.AZURE_CLIENT_SECRET}} \
  --tenant {{env.AZURE_TENANT_ID}}

az account set --subscription {{env.AZURE_SUBSCRIPTION_ID}}
```

Create an NSG:

```bash
az network nsg create \
  --name {{user.nsg_name}} \
  --resource-group {{user.resource_group}} \
  --location {{user.location}} \
  --output json
```

Create a security rule:

```bash
az network nsg rule create \
  --name {{user.rule_name}} \
  --nsg-name {{user.nsg_name}} \
  --resource-group {{user.resource_group}} \
  --priority {{user.priority}} \
  --direction {{user.direction}} \
  --access {{user.access}} \
  --protocol {{user.protocol}} \
  --source-address-prefixes {{user.source_address_prefixes}} \
  --source-port-ranges {{user.source_port_ranges}} \
  --destination-address-prefixes {{user.destination_address_prefixes}} \
  --destination-port-ranges {{user.destination_port_ranges}} \
  --output json
```

## Azure SDK Fallback Path

Use SDK fallback only after Azure CLI fails after up to 3 retries.

```python
from azure.identity import ClientSecretCredential
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import NetworkSecurityGroup, SecurityRule

credential = ClientSecretCredential(
    tenant_id="{{env.AZURE_TENANT_ID}}",
    client_id="{{env.AZURE_CLIENT_ID}}",
    client_secret="{{env.AZURE_CLIENT_SECRET}}",
)
client = NetworkManagementClient(credential, "{{env.AZURE_SUBSCRIPTION_ID}}")

poller = client.network_security_groups.begin_create_or_update(
    "{{user.resource_group}}",
    "{{user.nsg_name}}",
    NetworkSecurityGroup(location="{{user.location}}"),
)
nsg = poller.result()

rule_poller = client.security_rules.begin_create_or_update(
    "{{user.resource_group}}",
    "{{user.nsg_name}}",
    "{{user.rule_name}}",
    SecurityRule(
        priority={{user.priority}},
        direction="{{user.direction}}",
        access="{{user.access}}",
        protocol="{{user.protocol}}",
        source_address_prefix="{{user.source_address_prefix}}",
        source_port_range="{{user.source_port_range}}",
        destination_address_prefix="{{user.destination_address_prefix}}",
        destination_port_range="{{user.destination_port_range}}",
    ),
)
rule = rule_poller.result()
```

## Polling and Output

- Poll long-running operations every 15 seconds for up to 20 minutes.
- Capture raw JSON output and mask credentials as `***` in traces.
- Parse `{{output.nsg_id}}` from `.id`.
- Parse `{{output.rule_id}}` from `.id`.
