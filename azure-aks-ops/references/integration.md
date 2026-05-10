# Integration Setup (Azure AKS)

## Environment Setup

Azure AKS requires Azure CLI, Azure SDK, and kubectl for full operations.

### Install Azure CLI (One-time per machine)

```bash
# macOS
brew install azure-cli

# Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
# Download from: https://aka.ms/installazurecliwindows
```

### Install kubectl

```bash
# macOS
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Windows
# Download from: https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/

# Verify
kubectl version --client
```

### Install Azure SDK for Python

```bash
# Core packages
pip install azure-identity azure-mgmt-resource

# AKS-specific package
pip install azure-mgmt-containerservice

# Additional useful packages
pip install azure-mgmt-network    # For VNet integration
pip install azure-mgmt-monitor    # For monitoring
```

### Verify Installation

```bash
az --version
kubectl version --client
python -c "from azure.mgmt.containerservice import ContainerServiceClient; print('Azure SDK OK')"
```

## Credential Configuration

### Method A: Service Principal (Recommended for Automation)

```bash
# Create Service Principal with Contributor role
az ad sp create-for-rbac \
  --name "my-aks-automation-sp" \
  --role "Contributor" \
  --scopes "/subscriptions/{{subscription-id}}" \
  --output json
```

Output:
```json
{
  "appId": "{{AZURE_CLIENT_ID}}",
  "displayName": "my-aks-automation-sp",
  "password": "{{AZURE_CLIENT_SECRET}}",
  "tenant": "{{AZURE_TENANT_ID}}"
}
```

Store credentials:
```bash
export AZURE_SUBSCRIPTION_ID="{{subscription-id}}"
export AZURE_TENANT_ID="{{tenant-id}}"
export AZURE_CLIENT_ID="{{app-id}}"
export AZURE_CLIENT_SECRET="{{password}}"
```

### Method B: Azure CLI Login (Interactive)

```bash
az login
az account set --subscription "{{subscription-id}}"
az account show --output json
```

## AKS Cluster Access Setup

### Get Cluster Credentials

```bash
# Get admin credentials ( full access)
az aks get-credentials \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --admin \
  --output json

# Get user credentials ( limited access)
az aks get-credentials \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json

# Overwrite existing credentials
az aks get-credentials \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --overwrite-existing
```

### Verify Cluster Access

```bash
# Check current context
kubectl config current-context

# List available contexts
kubectl config get-contexts

# Switch context ( if multiple clusters)
kubectl config use-context {{context-name}}

# Test connectivity
kubectl cluster-info
kubectl get nodes
```

## Azure AD Integration Setup

### Enable Azure AD Authentication for AKS

```bash
# Create AKS with Azure AD integration
az aks create \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --enable-aad \
  --aad-admin-group-object-ids "{{group-object-id}}" \
  --output json
```

### Azure AD RBAC Roles for AKS

| Role | Permission |
|------|------------|
| AzureKubernetesServiceClusterAdminRole | Full admin access |
| AzureKubernetesServiceClusterUserRole | User access |
| AzureKubernetesServiceContributorRole | Manage cluster resources |

```bash
# Assign admin role to user/group
az role assignment create \
  --assignee "{{user-or-group-id}}" \
  --role "AzureKubernetesServiceClusterAdminRole" \
  --scope "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.ContainerService/managedClusters/{{aks}}"
```

## VNet Integration Setup (Azure CNI)

### Create VNet with Subnet for AKS

```bash
# Create VNet
az network vnet create \
  --name "{{vnet_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --address-prefixes "10.0.0.0/16" \
  --output json

# Create subnet with delegation
az network vnet subnet create \
  --name "{{subnet_name}}" \
  --vnet-name "{{vnet_name}}" \
  --resource-group "{{user.resource_group}}" \
  --address-prefixes "10.0.0.0/24" \
  --delegations "Microsoft.ContainerService/managedClusters" \
  --output json
```

### Create AKS with Azure CNI

```bash
az aks create \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --network-plugin azure \
  --vnet-subnet-id "/subscriptions/{{sub-id}}/resourceGroups/{{rg}}/providers/Microsoft.Network/virtualNetworks/{{vnet}}/subnets/{{subnet}}" \
  --output json
```

## ACR Integration Setup

### Create Azure Container Registry

```bash
# Create ACR
az acr create \
  --name "{{acr_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --sku Standard \
  --output json

# Attach ACR to AKS
az aks update \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --attach-acr "{{acr_name}}" \
  --output json
```

### Grant AKS Access to ACR

```bash
# Get ACR resource ID
ACR_ID=$(az acr show --name "{{acr_name}}" --resource-group "{{rg}}" --query "id" -o tsv)

# Assign AcrPull role to AKS service principal
az role assignment create \
  --assignee "{{aks-sp-id}}" \
  --role "AcrPull" \
  --scope "$ACR_ID"
```

## Monitoring Setup

### Enable Azure Monitor for Containers

```bash
# Create AKS with monitoring addon
az aks create \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --enable-addons monitoring \
  --output json

# Enable monitoring on existing cluster
az aks enable-addons \
  --addons monitoring \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --output json
```

### Create Log Analytics Workspace ( Optional)

```bash
# Create workspace
az monitor log-analytics workspace create \
  --name "{{workspace_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --output json

# Get workspace resource ID
WORKSPACE_ID=$(az monitor log-analytics workspace show --name "{{workspace_name}}" --resource-group "{{rg}}" --query "id" -o tsv)

# Enable monitoring with custom workspace
az aks enable-addons \
  --addons monitoring \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --workspace-resource-id "$WORKSPACE_ID"
```

## Private Cluster Setup

### Create Private AKS Cluster

```bash
az aks create \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --location "{{user.location}}" \
  --enable-private-cluster \
  --private-dns-zone "private" \
  --output json
```

### Configure Authorized IP Ranges

```bash
az aks create \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --api-server-authorized-ip-ranges "{{ip-range-1}},{{ip-range-2}}" \
  --output json

# Update authorized IP ranges on existing cluster
az aks update \
  --name "{{user.aks_name}}" \
  --resource-group "{{user.resource_group}}" \
  --api-server-authorized-ip-ranges "{{ip-range-1}},{{ip-range-2}}" \
  --output json
```

## Common Azure Regions for AKS

| Region Code | Display Name | Availability Zones |
|-------------|--------------|-------------------|
| eastus | East US | Yes |
| eastus2 | East US 2 | Yes |
| westus2 | West US 2 | Yes |
| centralus | Central US | Yes |
| westeurope | West Europe | Yes |
| northeurope | North Europe | Yes |
| southeastasia | Southeast Asia | Yes |
| eastasia | East Asia | Yes |
| japaneast | Japan East | Yes |
| australiaeast | Australia East | Yes |
| uksouth | UK South | Yes |
| francecentral | France Central | Yes |

Check availability:
```bash
az aks get-versions --location "{{location}}" --output json
```

## Project-based Setup (pyproject.toml)

```toml
[project]
name = "azure-aks-ops"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "azure-identity>=1.10.0",
    "azure-mgmt-resource>=21.0.0",
    "azure-mgmt-containerservice>=27.0.0",
    "azure-mgmt-network>=23.0.0",
    "azure-mgmt-monitor>=5.0.0",
]

[tool.uv]
python-version = "3.10"
```

Sync:
```bash
uv sync
source .venv/bin/activate
```

## Safety Rules

- **NEVER** commit `.env` files ( add to `.gitignore`)
- **NEVER** write credentials into Skill documents
- Generated Skills use `{{env.*}}` placeholders only
- Service Principal secrets should be rotated regularly
- kubectl config stored in `~/.kube/config` ( protect this file)

## Quick Reference Commands

```bash
# Create basic AKS cluster
az aks create --name myAKS --resource-group myRG --location eastus --node-count 3

# Get credentials
az aks get-credentials --name myAKS --resource-group myRG

# Scale nodes
az aks scale --name myAKS --resource-group myRG --node-count 5

# Check cluster
az aks show --name myAKS --resource-group myRG

# List clusters
az aks list

# Delete cluster
az aks delete --name myAKS --resource-group myRG --yes
```