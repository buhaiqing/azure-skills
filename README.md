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

├── azure-vnet-ops/                  # Virtual Network Operations Skill
│   ├── SKILL.md                     # Concise - VNet, subnet, peering
│   ├── references/
│   │   ├── core-concepts.md         # Address spaces, subnets, peering
│   │   ├── troubleshooting.md      # CIDR overlap, dependencies, peering issues
│   │   ├── integration.md           # Network Contributor setup
│   │   ├── rubric.md                # GCL scoring rubric
│   │   └── prompt-templates.md      # GCL Generator/Critic prompts
│   └── assets/
│       └── example-config.yaml      # VNet/subnet examples

├── azure-loadbalancer-ops/          # Load Balancer Operations Skill
│   ├── SKILL.md                     # Concise - L4 load balancing
│   ├── references/
│   │   ├── core-concepts.md         # Load Balancer types, SKU
│   │   ├── troubleshooting.md      # Backend pool, health probe issues
│   │   └── integration.md           # Service Principal setup
│   └── assets/
│       └── example-config.yaml      # Public/Internal LB examples

├── azure-nsg-ops/                   # Network Security Group Operations Skill
│   ├── SKILL.md                     # Concise - NSG rules and associations
│   ├── references/
│   │   ├── core-concepts.md         # Rules, priorities, associations
│   │   ├── troubleshooting.md      # Effective rules and traffic diagnosis
│   │   ├── integration.md           # Network Contributor setup
│   │   ├── rubric.md                # GCL scoring rubric
│   │   └── prompt-templates.md      # GCL Generator/Critic prompts
│   └── assets/
│       └── example-config.yaml      # NSG/rule/association examples

├── azure-privateendpoint-ops/       # Private Endpoint Operations Skill
│   ├── SKILL.md                     # Concise - Private Link connectivity
│   ├── references/
│   │   ├── core-concepts.md         # Private Endpoint, DNS, connection states
│   │   ├── troubleshooting.md      # Approval, DNS, subnet issues
│   │   ├── integration.md           # Network and DNS RBAC setup
│   │   ├── rubric.md                # GCL scoring rubric
│   │   └── prompt-templates.md      # GCL Generator/Critic prompts
│   └── assets/
│       └── example-config.yaml      # Private Endpoint/DNS examples

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
├── azure-appservice-ops/            # Azure App Service Operations Skill
│   ├── SKILL.md                     # Concise - Web Apps and plans
│   ├── references/
│   │   ├── core-concepts.md         # Plans, Web Apps, slots, settings
│   │   ├── troubleshooting.md      # Runtime, scale, slot, log issues
│   │   ├── integration.md           # Website Contributor setup
│   │   ├── rubric.md                # GCL scoring rubric
│   │   └── prompt-templates.md      # GCL Generator/Critic prompts
│   └── assets/
│       └── example-config.yaml      # Web App/plan examples
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
├── azure-sqldb-ops/                 # Azure SQL Database Operations Skill
│   ├── SKILL.md                     # Concise - Logical server, elastic pool
│   ├── references/
│   │   ├── core-concepts.md         # Logical server, database, elastic pool
│   │   ├── troubleshooting.md      # Connections, DTU/CPU, deadlocks, query RCA
│   │   ├── aiops.md                # Metrics/query correlation and RCA reports
│   │   └── integration.md           # CLI/SDK, RBAC, polling
│   └── assets/
│       └── example-config.yaml      # SQL DB/elastic pool examples
│
├── azure-function-ops/              # Azure Functions Operations Skill
│   ├── SKILL.md                     # Concise - Serverless functions
│   ├── references/
│   │   ├── cli-reference.md         # CLI commands + SDK fallback
│   │   ├── core-concepts.md         # Hosting plans, triggers, bindings
│   │   ├── troubleshooting.md      # Cold start, timeout, deploy failures
│   │   └── integration.md          # SDK/CLI, RBAC (verified SDK methods)
│   └── assets/
│       └── example-config.yaml      # Consumption/Premium/Dedicated examples
│
├── azure-cosmos-ops/                # Azure Cosmos DB Operations Skill
│   ├── SKILL.md                     # Concise - NoSQL database
│   ├── references/
│   │   ├── core-concepts.md         # API models, RU/s, partition key, global dist
│   │   ├── troubleshooting.md      # 429, partition hot key, cross-region conflict
│   │   ├── aiops.md                # RU tuning, partition skew, throughput
│   │   └── integration.md          # SDK/CLI, data-plane (verified SDK methods)
│   └── assets/
│       └── example-config.yaml      # SQL API/manual-autoscale examples
│
├── azure-aci-ops/                   # Azure Container Instances Operations Skill
│   ├── SKILL.md                     # Concise - Serverless containers
│   ├── references/
│   │   ├── core-concepts.md         # Container groups, images, networking, volumes
│   │   ├── troubleshooting.md      # Image pull, OOM, crash, network, quota
│   │   └── integration.md          # SDK/CLI, registry auth (verified SDK)
│   └── assets/
│       └── example-config.yaml      # Public/private/registry container examples
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

# Virtual Network Examples
az network vnet create --name my-vnet --resource-group my-rg --location eastus --address-prefixes 10.20.0.0/16 --subnet-name app-subnet --subnet-prefixes 10.20.1.0/24 --output json
az network vnet subnet list --vnet-name my-vnet --resource-group my-rg --output json

# App Service Examples
az appservice plan create --name my-plan --resource-group my-rg --location eastus --sku B1 --is-linux --output json
az webapp create --name my-webapp --resource-group my-rg --plan my-plan --runtime "PYTHON:3.11" --output json

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
az ad sp create-for-rbac --name "my-automation-sp" --role "Contributor" --scopes "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" --output json

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
| azure-vnet-ops | Virtual Network (VNet, subnets, peering) | ✅ Complete |
| azure-loadbalancer-ops | Load Balancer (L4) | ✅ Complete |
| azure-nsg-ops | Network Security Group (NSG rules and associations) | ✅ Complete |
| azure-privateendpoint-ops | Private Endpoint (Private Link and DNS integration) | ✅ Complete |
| azure-appgateway-ops | Application Gateway (L7 + WAF) | ✅ Complete |
| azure-frontdoor-ops | Front Door (Global + CDN) | ✅ Complete |
| azure-trafficmanager-ops | Traffic Manager (DNS Routing) | ✅ Complete |
| azure-monitor-ops | Azure Monitor (Metrics/Alerts/Logs) | ✅ Complete |
| azure-aks-ops | Azure Kubernetes Service (AKS) | ✅ Complete |
| azure-blobstorage-ops | Azure Blob Storage | ✅ Complete |
| azure-vm-ops | Azure Virtual Machine | ✅ Complete |
| azure-appservice-ops | Azure App Service (Web Apps, plans, slots) | ✅ Complete |
| azure-redis-ops | Azure Redis (Cache operations, AIOps, RCA) | ✅ Complete |
| azure-postgres-ops | Azure PostgreSQL Flexible Server (DB operations, AIOps, RCA) | ✅ Complete |
| azure-acr-ops | Azure Container Registry (Image operations, AIOps, RCA) | ✅ Complete |
| azure-keyvault-ops | Azure Key Vault (Secrets, keys, certificates, AIOps, RCA) | ✅ Complete |
| azure-sqldb-ops | Azure SQL Database (with Elastic Pool) | ✅ Complete |
| azure-function-ops | Azure Functions (Serverless, dual-path, GCL) | ✅ Complete |
| azure-cosmos-ops | Azure Cosmos DB (RU/s, partition, global dist, GCL) | ✅ Complete |
| azure-aci-ops | Azure Container Instances (Serverless containers, GCL) | ✅ Complete |

## Planned Skills (Roadmap)

以下服务尚未封装，按优先级排布，作为后续扩展清单。每个 skill 仍需遵守 `azure-skill-generator` 脚手架与 2-round self-review 流程。

### P1 — 强烈建议（高频 + 高价值/高风险）

| Skill | Service | 备注 |
|------|------|------|
| azure-servicebus-ops | Azure Service Bus | 消息/死信队列/配额排障 |
| azure-eventhub-ops | Azure Event Hubs | 事件流式摄取，分区与吞吐排障 |

### P2 — 建议封装（中高频运维刚需）

| Skill | Service | 备注 |
|------|------|------|
| azure-queue-storage-ops | Queue Storage | 数据平面，与 blob-ops 互补 |
| azure-file-storage-ops | File Storage (SMB/NFS) | 迁移/挂载排障常见 |
| azure-backup-ops | Recovery Services / Backup | 备份/还原点；业务关键，GCL 建议启用 |
| azure-site-recovery-ops | Site Recovery (ASR) | 容灾编排，变更影响大 |
| azure-dns-ops | Azure DNS Zones | 与 TM/Front Door 互补，解析排障独立成块 |

### P3 — 可选（视场景）

| Skill | Service | 备注 |
|------|------|------|
| azure-logicapps-ops | Logic Apps | 集成/工作流自动化 |
| azure-eventgrid-ops | Event Grid | 事件路由 |
| azure-apim-ops | API Management | 企业 API 网关 |
| azure-synapse-ops | Synapse Analytics | 数据分析，体量大可分阶段 |
| azure-iot-hub-ops | IoT Hub | 涉 IoT 场景再补 |

## Compute Services Comparison

| Feature | Virtual Machine | App Service | AKS | Container Instances |
|---------|-----------------|-------------|-----|---------------------|
| **Type** | IaaS (full server) | PaaS web hosting | Managed K8s | Serverless containers |
| **Control** | Full OS control | Managed runtime/platform | Container orchestration | Single containers |
| **Scale** | Manual/auto-scale | Plan workers/SKU/autoscale | Auto-scaling clusters | Manual scaling |
| **Persistence** | Persistent disks | App config + mounted storage | Persistent volumes | Ephemeral |
| **Use Case** | Traditional apps, full control | Web apps/APIs | Microservices, complex apps | Simple tasks, batch jobs |

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

## Networking Services Comparison

| Feature | Virtual Network | NSG | Private Endpoint | Load Balancer | App Gateway | Front Door | Traffic Manager |
|---------|-----------------|-----|------------------|---------------|-------------|------------|-----------------|
| **Layer** | Network foundation | L3/L4 filtering | Private Link access | L4 (TCP/UDP) | L7 (HTTP/HTTPS) | L7 (HTTP/HTTPS) | DNS |
| **Scope** | Single Location / peered VNets | Subnet/NIC | Subnet to target resource | Single Location | Single Location | Global | Global |
| **Primary Use** | Address spaces, subnets, private connectivity | Allow/deny traffic rules | Private service connectivity | VM/backend load balancing | Web ingress + WAF | Global acceleration | DNS failover/routing |
| **Owns Subnets** | Yes | Associates to subnets/NICs | Allocates private IP in subnet | No | Requires dedicated subnet | No | No |
| **Destructive Risk** | Breaks attached resources | Blocks or exposes traffic | Breaks private connectivity | Traffic disruption | Traffic disruption | Global traffic impact | DNS routing impact |

## Load Balancing Services Comparison

| Feature | Load Balancer | App Gateway | Front Door | Traffic Manager |
|---------|---------------|-------------|------------|-----------------|
| **Layer** | L4 (TCP/UDP) | L7 (HTTP/HTTPS) | L7 (HTTP/HTTPS) | DNS |
| **Scope** | Single Location | Single Location | Global | Global |
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