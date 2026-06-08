# Azure Private Endpoint Integration

## Required Environment

Never ask the user to paste secrets. Read credentials only from runtime environment variables.

```bash
export AZURE_SUBSCRIPTION_ID="{{env.AZURE_SUBSCRIPTION_ID}}"
export AZURE_TENANT_ID="{{env.AZURE_TENANT_ID}}"
export AZURE_CLIENT_ID="{{env.AZURE_CLIENT_ID}}"
export AZURE_CLIENT_SECRET="{{env.AZURE_CLIENT_SECRET}}"
```

## RBAC

Minimum recommended roles:

- **Network Contributor** on the Resource Group that owns the Private Endpoint and subnet.
- Target service approval permission, such as owner/contributor on the target resource or service-specific Private Endpoint connection approval permission.
- **Private DNS Zone Contributor** when creating or deleting DNS zone groups that reference private DNS zones.

## Azure CLI Primary Path

Authenticate and select subscription:

```bash
az login --service-principal \
  --username {{env.AZURE_CLIENT_ID}} \
  --password {{env.AZURE_CLIENT_SECRET}} \
  --tenant {{env.AZURE_TENANT_ID}}

az account set --subscription {{env.AZURE_SUBSCRIPTION_ID}}
```

Create a Private Endpoint:

```bash
az network private-endpoint create \
  --name {{user.private_endpoint_name}} \
  --resource-group {{user.resource_group}} \
  --location {{user.location}} \
  --subnet {{user.subnet_id}} \
  --private-connection-resource-id {{user.private_link_resource_id}} \
  --group-id {{user.group_id}} \
  --connection-name {{user.connection_name}} \
  --output json
```

Create a private DNS zone group:

```bash
az network private-endpoint dns-zone-group create \
  --endpoint-name {{user.private_endpoint_name}} \
  --resource-group {{user.resource_group}} \
  --name {{user.dns_zone_group_name}} \
  --private-dns-zone {{user.private_dns_zone_id}} \
  --zone-name {{user.private_dns_zone_name}} \
  --output json
```

## Azure SDK Fallback Path

Use SDK fallback only after Azure CLI fails after up to 3 retries.

```python
from azure.identity import ClientSecretCredential
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import PrivateEndpoint, PrivateLinkServiceConnection, Subnet

credential = ClientSecretCredential(
    tenant_id="{{env.AZURE_TENANT_ID}}",
    client_id="{{env.AZURE_CLIENT_ID}}",
    client_secret="{{env.AZURE_CLIENT_SECRET}}",
)
client = NetworkManagementClient(credential, "{{env.AZURE_SUBSCRIPTION_ID}}")

poller = client.private_endpoints.begin_create_or_update(
    "{{user.resource_group}}",
    "{{user.private_endpoint_name}}",
    PrivateEndpoint(
        location="{{user.location}}",
        subnet=Subnet(id="{{user.subnet_id}}"),
        private_link_service_connections=[
            PrivateLinkServiceConnection(
                name="{{user.connection_name}}",
                private_link_service_id="{{user.private_link_resource_id}}",
                group_ids=["{{user.group_id}}"],
            )
        ],
    ),
)
private_endpoint = poller.result()
```

Private Endpoint connection approval APIs can be service-specific. Use the target service management client only when the SDK method is verified for that resource type; otherwise HALT and report the supported CLI/API path required.

## Polling and Output

- Poll long-running operations every 15 seconds for up to 30 minutes.
- Capture raw JSON output and mask credentials as `***` in traces.
- Parse `{{output.private_endpoint_id}}` from `.id`.
- Parse `{{output.connection_state}}` from `.privateLinkServiceConnections[].privateLinkServiceConnectionState.status`.
