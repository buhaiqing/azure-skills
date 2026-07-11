# CLI & SDK Reference — azure-function-ops

Detailed CLI and Azure SDK for Python (azure-mgmt-web) commands for operations whose
slim entrypoints live in `SKILL.md`. SKILL.md keeps triggers, scope, flow, safety gates,
and links; this file holds the command detail. All operations require `--resource-group`
and (for functionapp) `--name`, and use `--output json`.

## Deploy Code

Zip deploy pushes a local package to the Function App. Non-destructive to slots unless you
deploy directly to a production app without a swap plan — verify the target first.

### Azure CLI (Primary)

```bash
# Zip deploy (recommended)
az functionapp deployment source config-zip \
  --name "{{user.function_app_name}}" \
  --resource-group "{{user.resource_group}}" \
  --src "{{user.zip_path}}" \
  --output json
```

### Azure SDK for Python (Fallback)

The Azure SDK (`azure-mgmt-web`) has no first-class zip-publish method. Use the **OneDeploy**
extension (`create_one_deploy_operation`) to push the zip package, or fall back to the Kudu
zip-deploy REST endpoint. Push the zip bytes via OneDeploy:

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.web import WebSiteManagementClient

credential = DefaultAzureCredential()
client = WebSiteManagementClient(
    credential,
    subscription_id=os.environ['AZURE_SUBSCRIPTION_ID'],
)

# OneDeploy zip push to the Function App
with open('{{user.zip_path}}', 'rb') as f:
    client.web_apps.create_one_deploy_operation(
        resource_group_name='{{user.resource_group}}',
        name='{{user.function_app_name}}',
        type='zip',
        content=f.read(),
    )
```

> `create_one_deploy_operation` is **not** a `begin_*` LRO — it returns when the deploy is
> accepted. Poll deployment status via `client.web_apps.list_deployments(...)` or the Kudu
> API. Retry up to 3× with backoff before reporting failure.

## Restart Function App

### Azure CLI (Primary)

```bash
az functionapp restart \
  --name "{{user.function_app_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### Azure SDK for Python (Fallback)

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.web import WebSiteManagementClient

credential = DefaultAzureCredential()
client = WebSiteManagementClient(
    credential,
    subscription_id=os.environ['AZURE_SUBSCRIPTION_ID'],
)

client.web_apps.restart(
    resource_group_name='{{user.resource_group}}',
    name='{{user.function_app_name}}',
)
```

## Show / List

### Azure CLI (Primary)

```bash
# Show a single Function App
az functionapp show \
  --name "{{user.function_app_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# List all Function Apps in a Resource Group
az functionapp list \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### Azure SDK for Python (Fallback)

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.web import WebSiteManagementClient

credential = DefaultAzureCredential()
client = WebSiteManagementClient(
    credential,
    subscription_id=os.environ['AZURE_SUBSCRIPTION_ID'],
)

# Show a single Function App
app = client.web_apps.get(
    resource_group_name='{{user.resource_group}}',
    name='{{user.function_app_name}}',
)

# List all Function Apps in a Resource Group
apps = client.web_apps.list_by_resource_group(
    resource_group_name='{{user.resource_group}}',
)
```
