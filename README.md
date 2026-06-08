# Azure Skills Repository

A collection of Azure cloud resource/service operation skills for AI Agent automated operation scenarios.

🌐 [中文版本](./README_cn.md)

## Project Structure

```
azure-skills/
├── azure-skill-generator/           # Meta Skill (Skill Generator)
│   ├── SKILL.md                     # Concise - What to do
│   ├── scripts/
│   │   └── setup_env.py             # .env → config generator
│   ├── references/                  # Detailed - How to do
│   │   ├── azure-skill-template.md  # Skill skeleton template
│   │   ├── azure-cli-conventions.md # CLI behavior conventions
│   │   ├── azure-sdk-usage.md       # SDK usage patterns (Python)
│   │   ├── integration.md           # Environment setup
│   │   ├── core-concepts-template.md
│   │   ├── troubleshooting-template.md
│   │   └── governance-review.md     # Checklist
│   └── assets/
│       └── example-config.yaml

├── azure-loadbalancer-ops/          # Load Balancer Operations Skill
│   ├── SKILL.md                     # Concise - L4 load balancing
│   ├── references/
│   │   ├── core-concepts.md         # Load Balancer types, SKU
│   │   ├── troubleshooting.md      # Backend pool, health probe issues
│   │   └── integration.md           # Service Principal setup
│   └── assets/
│       └── example-config.yaml      # Public/Internal LB examples

├── azure-appgateway-ops/            # Application Gateway Operations Skill
│   ├── SKILL.md                     # Concise - L7 load balancing + WAF
│   ├── references/
│   │   ├── core-concepts.md         # AGW components, SKU
│   │   ├── troubleshooting.md      # Backend health, SSL, WAF issues
│   │   └── integration.md           # Dedicated subnet setup
│   └── assets/
│       └── example-config.yaml      # SSL/WAF/URL routing examples

├── azure-frontdoor-ops/             # Front Door Operations Skill
│   ├── SKILL.md                     # Concise - Global L7 + CDN
│   ├── references/
│   │   ├── core-concepts.md         # Front Door components, SKU
│   │   ├── troubleshooting.md      # Origin health, custom domain issues
│   │   └── integration.md           # Endpoint naming, WAF setup
│   └── assets/
│       └── example-config.yaml      # Global routing, CDN, WAF examples

├── azure-trafficmanager-ops/        # Traffic Manager Operations Skill
│   ├── SKILL.md                     # Concise - DNS load balancing
│   ├── references/
│   │   ├── core-concepts.md         # Routing methods, endpoint types
│   │   ├── troubleshooting.md      # DNS resolution, endpoint health
│   │   └── integration.md           # DNS naming, routing config
│   └── assets/
│       └── example-config.yaml      # Priority/Weighted/Geographic examples


├── azure-monitor-ops/              # Azure Monitor Operations Skill
│   ├── SKILL.md                     # Concise - Metrics, Alerts, Logs
│   ├── references/
│   │   ├── core-concepts.md         # Monitor components, KQL, Alert types
│   │   ├── troubleshooting.md      # Metric/alert/log query issues
│   │   └── integration.md           # SDK packages, permissions
│   └ assets/
│       └ example-config.yaml      # Alert/action group/diagnostic examples
│
├── azure-aks-ops/                   # Azure Kubernetes Service (AKS) Operations Skill
│   ├── SKILL.md                     # Concise - Managed Kubernetes
│   ├── references/
│   │   ├── core-concepts.md         # AKS architecture, node pools, networking
│   │   ├── troubleshooting.md      # Cluster/node pool issues, upgrade failures
│   │   └── integration.md           # kubectl setup, ACR integration, monitoring
│   └── assets/
│       └── example-config.yaml      # Basic/production/private cluster examples
│
├── azure-blobstorage-ops/           # Azure Blob Storage Operations Skill
│   ├── SKILL.md                     # Concise - Object storage
│   ├── references/
│   │   ├── core-concepts.md         # Storage tiers, blob types, replication
│   │   ├── troubleshooting.md      # Authentication, upload/download issues
│   │   └ integration.md             # AzCopy, SAS tokens, lifecycle management
│   └ assets/
│       └ example-config.yaml      # Storage account/container examples
│
├── azure-vm-ops/                    # Azure Virtual Machine Operations Skill
│   ├── SKILL.md                     # Concise - Compute instances
│   ├── references/
│   │   ├── core-concepts.md         # VM sizes, images, storage options
│   │   ├── troubleshooting.md      # Provisioning, connectivity, resize issues
│   │   └── integration.md           # SSH setup, extensions, resizing
│   └── assets/
│       └── example-config.yaml      # Linux/Windows VM examples
│
├── azure-redis-ops/                 # Azure Redis Operations Skill
│   ├── SKILL.md                     # Concise - Cache operations and RCA
│   ├── references/
│   │   ├── core-concepts.md         # SKUs, networking, metrics
│   │   ├── troubleshooting.md      # Latency, memory, eviction, connectivity RCA
│   │   ├── aiops.md                # Anomaly correlation and RCA reports
│   │   └── integration.md           # CLI/SDK, RBAC, polling
│   └── assets/
│       └── example-config.yaml      # Redis cache examples
│
├── azure-postgres-ops/              # Azure PostgreSQL Operations Skill
│   ├── SKILL.md                     # Concise - Flexible Server operations and RCA
│   ├── references/
│   │   ├── core-concepts.md         # Flexible Server, HA, backup, networking
│   │   ├── troubleshooting.md      # Connections, CPU, storage, query RCA
│   │   ├── aiops.md                # Metrics/query correlation and DBA review
│   │   └── integration.md           # CLI/SDK, RBAC, polling
│   └── assets/
│       └── example-config.yaml      # PostgreSQL server examples
│
├── azure-acr-ops/                   # Azure Container Registry Operations Skill
│   ├── SKILL.md                     # Concise - Registry operations and image pull RCA
│   ├── references/
│   │   ├── core-concepts.md         # Registry, repository, tag, identity, networking
│   │   ├── troubleshooting.md      # ImagePullBackOff, auth, network, purge RCA
│   │   ├── aiops.md                # Pull/auth anomaly correlation
│   │   └── integration.md           # CLI/SDK, RBAC, polling
│   └── assets/
│       └── example-config.yaml      # ACR registry examples
│
├── azure-keyvault-ops/              # Azure Key Vault Operations Skill
│   ├── SKILL.md                     # Concise - Vault operations and access RCA
│   ├── references/
│   │   ├── core-concepts.md         # Secrets, keys, certs, RBAC/access policies
│   │   ├── troubleshooting.md      # 403, network, expiry, lifecycle RCA
│   │   ├── aiops.md                # Denied request and expiry correlation
│   │   └── integration.md           # CLI/SDK, RBAC, polling
│   └── assets/
│       └── example-config.yaml      # Key Vault examples
│
├── azure-audit-ops/                # Azure Audit Operations Skill
│   ├── SKILL.md                     # Concise - Cross-product audit
│   ├── references/
│   │   ├── core-concepts.md         # Activity Log, RBAC, Locks, Policy, Security
│   │   ├── troubleshooting.md      # Permissions, throttling, empty results
│   │   └── integration.md           # Reader role setup, SDK packages
│   ├── assets/
│   │   └── example-config.yaml      # Audit report examples
│   │
├── azure-cost-ops/                  # Azure Cost Operations Skill
│   ├── SKILL.md                     # Concise - Cost management & billing
│   ├── references/
│   │   ├── core-concepts.md         # Cost scopes, billing models, FinOps
│   │   ├── troubleshooting.md      # Permissions, empty results, budgets
│   │   └── integration.md           # Cost Management Reader role
│   └── assets/
│       └── example-config.yaml      # Cost analysis & budget examples
│
└── azure-[service]-ops/             # More service skills...
```

## Design Principles

### SKILL.md Concise
- Focus only on **What to do**: trigger conditions, scope, execution flow overview
- ~100-150 lines for quick Agent comprehension

### References for Details
- **How to do**: CLI commands, SDK code, troubleshooting, etc.
- Detailed implementation in separate files, loaded on demand

### Dual-Path Execution
- **Primary**: Azure CLI (`az [service] [command]`)
- **Fallback**: Azure SDK for Python (3 retries after CLI failure)

### Workflow Pattern
```
Pre-flight → Execute → Validate → Recover
```

## Quick Start

### Generate New Skills with Meta Skill

When Agent loads `azure-skill-generator`, provide the following:

```
Product: Azure [Service Name]
Primary Resource: [Resource Type]
Official Docs: https://docs.microsoft.com/azure/[service]/
CLI Support: az [service] --help
SDK Module: azure.mgmt.[service]
Operations: create, show, update, delete, list
```

Agent will automatically generate `azure-[service]-ops` directory structure.

### Use Existing Skills

After loading the corresponding skill, Agent can execute:

```bash
# Load Balancer Examples
az network lb create --name my-lb --resource-group my-rg --location eastus --output json
az network lb show --name my-lb --resource-group my-rg --output json

# Application Gateway Examples
az network application-gateway create --name my-agw --resource-group my-rg --location eastus --output json
az network application-gateway show-backend-health --gateway-name my-agw --resource-group my-rg

# Front Door Examples
az afd profile create --profile-name my-fd --resource-group my-rg --sku Standard_AzureFrontDoor --output json
az afd endpoint create --endpoint-name my-endpoint --profile-name my-fd --resource-group my-rg

# Traffic Manager Examples
az network traffic-manager profile create --name my-tm --resource-group my-rg --routing-method Performance --output json
az network traffic-manager endpoint create --name endpoint-1 --profile-name my-tm --resource-group my-rg --type externalEndpoints --target myapp.azurewebsites.net

# AKS Examples
az aks create --name my-aks --resource-group my-rg --location eastus --node-count 3 --generate-ssh-keys --output json
az aks get-credentials --name my-aks --resource-group my-rg

# Blob Storage Examples
az storage account create --name mystorage --resource-group my-rg --location eastus --sku Standard_LRS --kind StorageV2 --output json
az storage container create --name my-container --account-name mystorage
az storage blob upload --account-name mystorage --container-name my-container --name myblob --file myfile.txt

# Virtual Machine Examples
az vm create --name my-vm --resource-group my-rg --location eastus --image Ubuntu2204 --size Standard_DS2_v2 --generate-ssh-keys --output json
az vm list --resource-group my-rg --output json
az vm stop --name my-vm --resource-group my-rg  # Stop and deallocate (stops billing)
```

## Environment Setup

**Prerequisites**: Python >= 3.10

### Quick Setup with .env (Recommended)

```bash
# One-time: copy .env.example → .env and generate config
python azure-skill-generator/scripts/setup_env.py

# Edit .env and fill in your Azure credentials, then re-render
python azure-skill-generator/scripts/setup_env.py --render

# Verify credentials are valid
python azure-skill-generator/scripts/setup_env.py --check
```

This generates `azure-skill-generator/config.yaml` with your actual credential values and resolves `{{env.*}}` placeholders in template files.

### Manual Setup

```bash
# Install Azure CLI
# macOS
brew install azure-cli

# Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Create Service Principal for automation
az ad sp create-for-rbac --name "my-automation-sp" --role "Contributor" --scopes "/subscriptions/{{subscription-id}}" --output json

# Configure credentials
export AZURE_SUBSCRIPTION_ID="your_subscription_id"
export AZURE_TENANT_ID="your_tenant_id"
export AZURE_CLIENT_ID="your_client_id"
export AZURE_CLIENT_SECRET="your_client_secret"

# Verify
az account show --output json
```

## Existing Skills

| Skill | Service | Status |
|------|------|------|
| azure-cost-ops | Azure Cost Management (Billing, Budgets, Reservations) | ✅ Complete |
| azure-audit-ops | Azure Audit (Activity Log, RBAC, Locks, Policy, Security) | ✅ Complete |
| azure-skill-generator | Meta Skill | ✅ Complete |
| azure-loadbalancer-ops | Load Balancer (L4) | ✅ Complete |
| azure-appgateway-ops | Application Gateway (L7 + WAF) | ✅ Complete |
| azure-frontdoor-ops | Front Door (Global + CDN) | ✅ Complete |
| azure-trafficmanager-ops | Traffic Manager (DNS Routing) | ✅ Complete |
| azure-monitor-ops | Azure Monitor (Metrics/Alerts/Logs) | ✅ Complete |
| azure-aks-ops | Azure Kubernetes Service (AKS) | ✅ Complete |
| azure-blobstorage-ops | Azure Blob Storage | ✅ Complete |
| azure-vm-ops | Azure Virtual Machine | ✅ Complete |
| azure-redis-ops | Azure Redis (Cache operations, AIOps, RCA) | ✅ Complete |
| azure-postgres-ops | Azure PostgreSQL Flexible Server (DB operations, AIOps, RCA) | ✅ Complete |
| azure-acr-ops | Azure Container Registry (Image operations, AIOps, RCA) | ✅ Complete |
| azure-keyvault-ops | Azure Key Vault (Secrets, keys, certificates, AIOps, RCA) | ✅ Complete |

## Compute Services Comparison

| Feature | Virtual Machine | AKS | Container Instances |
|---------|-----------------|-----|---------------------|
| **Type** | IaaS (full server) | Managed K8s | Serverless containers |
| **Control** | Full OS control | Container orchestration | Single containers |
| **Scale** | Manual/auto-scale | Auto-scaling clusters | Manual scaling |
| **Persistence** | Persistent disks | Persistent volumes | Ephemeral |
| **Use Case** | Traditional apps, full control | Microservices, complex apps | Simple tasks, batch jobs |

## Storage Services Comparison

| Feature | Blob Storage | File Storage | Disk Storage |
|---------|--------------|--------------|--------------|
| **Type** | Object storage | SMB file shares | Block storage |
| **Access** | REST API/SAS | SMB/NFS protocol | VM-attached |
| **Scale** | Massive scale (5 PB+) | Limited per share | Per VM limits |
| **Use Case** | Documents, images, backup | File shares, migration | VM OS/data disks |

## Container Services Comparison

| Feature | AKS | Container Instances |
|---------|-----|---------------------|
| **Orchestration** | Full Kubernetes | Single containers |
| **Scale** | Auto-scaling clusters | Manual scaling |
| **Management** | Managed K8s | Serverless containers |
| **Use Case** | Microservices, complex apps | Simple tasks, batch jobs |
| **Integration** | ACR, Helm, Istio | ACR, simple deployments |

## Load Balancing Services Comparison

| Feature | Load Balancer | App Gateway | Front Door | Traffic Manager |
|---------|---------------|-------------|------------|-----------------|
| **Layer** | L4 (TCP/UDP) | L7 (HTTP/HTTPS) | L7 (HTTP/HTTPS) | DNS |
| **Scope** | Single region | Single region | Global | Global |
| **CDN** | No | No | Yes | No |
| **WAF** | No | Yes | Premium | No |
| **SSL Termination** | No | Yes | Yes | At endpoint |
| **URL Routing** | No | Yes | Yes | No |
| **Use Case** | VM load balancing | Web apps | Global acceleration | Failover/Geographic routing |

## Azure vs AWS Comparison

| Aspect | Azure | AWS |
|---------|-------|-----|
| CLI tool | `az` | `aws` |
| Primary SDK | Azure SDK for Python | boto3 |
| Auth method | Service Principal / Azure AD | IAM User / Role |
| Resource ID | `/subscriptions/.../providers/...` | `arn:aws:...` |
| Region term | **Location** | Region |
| Container | **Resource Group** (required) | No equivalent |
| L4 LB | Load Balancer | ELB (NLB/CLB) |
| L7 LB | Application Gateway | ELB (ALB) |
| Global LB | Front Door | CloudFront (CDN) + Route 53 |
| DNS LB | Traffic Manager | Route 53 |

## References

- [Azure CLI Documentation](https://docs.microsoft.com/cli/azure/)
- [Azure SDK for Python](https://docs.microsoft.com/python/api/overview/azure/)
- [Azure REST API Reference](https://docs.microsoft.com/rest/api/azure/)
- [Agent Skills OpenSpec](https://agentskills.io/specification)

## License

MIT