# Azure Skills Repository

Azure 云资源/云服务操作技能集合，用于 AI Agent 自动化运维场景。

🌐 [English Version](./README.md)

## 项目结构

```
azure-skills/
├── azure-skill-generator/           # Meta Skill (技能生成器)
│   ├── SKILL.md                     # 精简版 - What to do
│   ├── scripts/
│   │   └── setup_env.py             # .env → 配置生成器
│   ├── references/                  # 详细实现 - How to do
│   │   ├── azure-skill-template.md  # 技能骨架模板
│   │   ├── azure-cli-conventions.md # CLI 行为规范
│   │   ├── azure-sdk-usage.md       # SDK 使用模式 (Python)
│   │   ├── integration.md           # 环境设置
│   │   ├── core-concepts-template.md
│   │   ├── troubleshooting-template.md
│   │   └── governance-review.md     # 检查清单
│   └ assets/
│       └ example-config.yaml

├── azure-vnet-ops/                  # Virtual Network 操作技能
│   ├── SKILL.md                     # 精简版 - VNet、子网、对等互连
│   ├── references/
│   │   ├── core-concepts.md         # 地址空间、子网、对等互连
│   │   ├── troubleshooting.md      # CIDR 重叠、依赖、对等互连问题
│   │   ├── integration.md           # Network Contributor 设置
│   │   ├── rubric.md                # GCL 评分规则
│   │   └── prompt-templates.md      # GCL Generator/Critic 提示词
│   └ assets/
│       └ example-config.yaml       # VNet/子网示例

├── azure-loadbalancer-ops/          # Load Balancer 操作技能
│   ├── SKILL.md                     # 精简版 - L4 负载均衡
│   ├── references/
│   │   ├── core-concepts.md         # 负载均衡器类型、SKU
│   │   ├── troubleshooting.md      # 后端池、健康探测问题
│   │   └ integration.md             # Service Principal 设置
│   └ assets/
│       └ example-config.yaml       # 公网/内网负载均衡器示例

├── azure-nsg-ops/                   # Network Security Group 操作技能
│   ├── SKILL.md                     # 精简版 - NSG 规则与关联
│   ├── references/
│   │   ├── core-concepts.md         # 规则、优先级、关联
│   │   ├── troubleshooting.md      # 有效规则与流量诊断
│   │   ├── integration.md           # Network Contributor 设置
│   │   ├── rubric.md                # GCL 评分规则
│   │   └── prompt-templates.md      # GCL Generator/Critic 提示词
│   └ assets/
│       └ example-config.yaml       # NSG/规则/关联示例

├── azure-privateendpoint-ops/       # Private Endpoint 操作技能
│   ├── SKILL.md                     # 精简版 - Private Link 连接
│   ├── references/
│   │   ├── core-concepts.md         # Private Endpoint、DNS、连接状态
│   │   ├── troubleshooting.md      # 审批、DNS、子网问题
│   │   ├── integration.md           # 网络与 DNS RBAC 设置
│   │   ├── rubric.md                # GCL 评分规则
│   │   └── prompt-templates.md      # GCL Generator/Critic 提示词
│   └ assets/
│       └ example-config.yaml       # Private Endpoint/DNS 示例

├── azure-appgateway-ops/            # Application Gateway 操作技能
│   ├── SKILL.md                     # 精简版 - L7 负载均衡 + WAF
│   ├── references/
│   │   ├── core-concepts.md         # AGW 组件、SKU
│   │   ├── troubleshooting.md      # 后端健康、SSL、WAF 问题
│   │   └ integration.md             # 专用子网设置
│   └ assets/
│       └ example-config.yaml       # SSL/WAF/URL 路由示例

├── azure-frontdoor-ops/             # Front Door 操作技能
│   ├── SKILL.md                     # 精简版 - 全球 L7 + CDN
│   ├── references/
│   │   ├── core-concepts.md         # Front Door 组件、SKU
│   │   ├── troubleshooting.md      # 源健康、自定义域名问题
│   │   └ integration.md             # 端点命名、WAF 设置
│   └ assets/
│       └ example-config.yaml       # 全球路由、CDN、WAF 示例

├── azure-trafficmanager-ops/        # Traffic Manager 操作技能
│   ├── SKILL.md                     # 精简版 - DNS 负载均衡
│   ├── references/
│   │   ├── core-concepts.md         # 路由方法、端点类型
│   │   ├── troubleshooting.md      # DNS 解析、端点健康
│   │   └ integration.md             # DNS 命名、路由配置
│   └ assets/
│       └ example-config.yaml       # 优先级/加权/地理路由示例

├── azure-monitor-ops/              # Azure Monitor 操作技能
│   ├── SKILL.md                     # 精简版 - 指标、告警、日志
│   ├── references/
│   │   ├── core-concepts.md         # Monitor组件、KQL、告警类型
│   │   ├── troubleshooting.md      # 指标/告警/日志查询问题
│   │   └ integration.md             # SDK包、权限配置
│   └ assets/
│       └ example-config.yaml       # 告警/操作组/诊断设置示例
│
├── azure-aks-ops/                   # Azure Kubernetes Service (AKS) 操作技能
│   ├── SKILL.md                     # 精简版 - 托管 Kubernetes
│   ├── references/
│   │   ├── core-concepts.md         # AKS 架构、节点池、网络
│   │   ├── troubleshooting.md      # 集群/节点池问题、升级失败
│   │   └── integration.md           # kubectl 设置、ACR 集成、监控
│   └ assets/
│       └ example-config.yaml       # 基础/生产/私有集群示例
│
├── azure-blobstorage-ops/           # Azure Blob Storage 操作技能
│   ├── SKILL.md                     # 精简版 - 对象存储
│   ├── references/
│   │   ├── core-concepts.md         # 存储层、Blob 类型、复制
│   │   ├── troubleshooting.md      # 鉴权、上传/下载问题
│   │   └ integration.md             # AzCopy、SAS、生命周期管理
│   └ assets/
│       └ example-config.yaml       # 存储账户/容器示例
│
├── azure-vm-ops/                    # Azure Virtual Machine 操作技能
│   ├── SKILL.md                     # 精简版 - 计算实例
│   ├── references/
│   │   ├── core-concepts.md         # VM 规格、镜像、存储选项
│   │   ├── troubleshooting.md      # 预配、连接、调整规格问题
│   │   └── integration.md           # SSH 设置、扩展、调整规格
│   └ assets/
│       └ example-config.yaml       # Linux/Windows VM 示例
│
├── azure-appservice-ops/            # Azure App Service 操作技能
│   ├── SKILL.md                     # 精简版 - Web App 与计划
│   ├── references/
│   │   ├── core-concepts.md         # 计划、Web App、槽位、配置
│   │   ├── troubleshooting.md      # 运行时、扩缩容、槽位、日志问题
│   │   ├── integration.md           # Website Contributor 设置
│   │   ├── rubric.md                # GCL 评分规则
│   │   └── prompt-templates.md      # GCL Generator/Critic 提示词
│   └ assets/
│       └ example-config.yaml       # Web App/计划示例
│
├── azure-audit-ops/                # Azure Audit 操作技能
│   ├── SKILL.md                     # 精简版 - 跨产品审计
│   ├── references/
│   │   ├── core-concepts.md         # Activity Log, RBAC, 锁, 策略, 安全
│   │   ├── troubleshooting.md      # 权限、限流、空结果
│   │   └ integration.md             # Reader 角色设置、SDK 包
│   └ assets/
│       └ example-config.yaml       # 审计报告示例
│
├── azure-cost-ops/                  # Azure Cost 操作技能
│   ├── SKILL.md                     # 精简版 - 成本管理与账单
│   ├── references/
│   │   ├── core-concepts.md         # 成本范围、账单模型、FinOps
│   │   ├── troubleshooting.md      # 权限、空结果、预算
│   │   └ integration.md             # Cost Management Reader 角色
│   └ assets/
│       └ example-config.yaml       # 成本分析与预算示例
│
├── azure-redis-ops/                 # Azure Redis 操作技能
│   ├── SKILL.md                     # 精简版 - 缓存运维与 RCA
│   ├── references/
│   │   ├── core-concepts.md         # SKU、网络、指标
│   │   ├── troubleshooting.md      # 延迟、内存、驱逐、连接 RCA
│   │   ├── aiops.md                # 异常关联与 RCA 报告
│   │   └ integration.md             # CLI/SDK、RBAC、轮询
│   └ assets/
│       └ example-config.yaml       # Redis 缓存示例
│
├── azure-postgres-ops/              # Azure PostgreSQL 操作技能
│   ├── SKILL.md                     # 精简版 - Flexible Server 运维与 RCA
│   ├── references/
│   │   ├── core-concepts.md         # Flexible Server、HA、备份、网络
│   │   ├── troubleshooting.md      # 连接、CPU、存储、查询 RCA
│   │   ├── aiops.md                # 指标/查询关联与 DBA 审核
│   │   └ integration.md             # CLI/SDK、RBAC、轮询
│   └ assets/
│       └ example-config.yaml       # PostgreSQL 服务示例
│
├── azure-acr-ops/                   # Azure Container Registry 操作技能
│   ├── SKILL.md                     # 精简版 - 镜像仓库运维与拉取 RCA
│   ├── references/
│   │   ├── core-concepts.md         # Registry、Repository、Tag、身份、网络
│   │   ├── troubleshooting.md      # ImagePullBackOff、鉴权、网络、清理 RCA
│   │   ├── aiops.md                # 拉取/鉴权异常关联
│   │   └ integration.md             # CLI/SDK、RBAC、轮询
│   └ assets/
│       └ example-config.yaml       # ACR 示例
│
├── azure-keyvault-ops/              # Azure Key Vault 操作技能
│   ├── SKILL.md                     # 精简版 - 密钥库运维与访问 RCA
│   ├── references/
│   │   ├── core-concepts.md         # Secret、Key、Certificate、RBAC/访问策略
│   │   ├── troubleshooting.md      # 403、网络、过期、生命周期 RCA
│   │   ├── aiops.md                # 拒绝请求与证书过期关联
│   │   └ integration.md             # CLI/SDK、RBAC、轮询
│   └ assets/
│       └ example-config.yaml       # Key Vault 示例
│
├── azure-sqldb-ops/                 # Azure SQL 数据库操作技能
│   ├── SKILL.md                     # 精简版 - 逻辑服务器、弹性池
│   ├── references/
│   │   ├── core-concepts.md         # 逻辑服务器、数据库、弹性池
│   │   ├── troubleshooting.md      # 连接、DTU/CPU、死锁、查询 RCA
│   │   ├── aiops.md                # 指标/查询关联与 RCA 报告
│   │   └── integration.md           # CLI/SDK、RBAC、轮询
│   └ assets/
│       └ example-config.yaml       # SQL 数据库/弹性池示例
│
├── azure-function-ops/              # Azure Functions 操作技能
│   ├── SKILL.md                     # 精简版 - Serverless 函数
│   ├── references/
│   │   ├── cli-reference.md         # CLI 命令 + SDK 回退
│   │   ├── core-concepts.md         # 托管计划、触发器、绑定
│   │   ├── troubleshooting.md      # 冷启动、超时、部署失败
│   │   └ integration.md             # SDK/CLI、RBAC（SDK 方法已校验）
│   └ assets/
│       └ example-config.yaml       # Consumption/Premium/Dedicated 示例
│
├── azure-cosmos-ops/                # Azure Cosmos DB 操作技能
│   ├── SKILL.md                     # 精简版 - NoSQL 数据库
│   ├── references/
│   │   ├── core-concepts.md         # API 模型、RU/s、分区键、全局分布
│   │   ├── troubleshooting.md      # 429、分区热点、跨区域冲突
│   │   ├── aiops.md                # RU 调优、分区倾斜、归一化吞吐
│   │   └ integration.md             # SDK/CLI、数据面（SDK 方法已校验）
│   └ assets/
│       └ example-config.yaml       # SQL API/手动-自动缩放示例
│
└── azure-aci-ops/                   # Azure Container Instances 操作技能
│   ├── SKILL.md                     # 精简版 - Serverless 容器
│   ├── references/
│   │   ├── core-concepts.md         # 容器组、镜像、网络、卷
│   │   ├── troubleshooting.md      # 镜像拉取、OOM、崩溃、网络、配额
│   │   └ integration.md             # SDK/CLI、Registry 认证（SDK 方法已校验）
│   └ assets/
│       └ example-config.yaml       # 公共/私有/registry 容器示例
│
├── azure-servicebus-ops/            # Azure Service Bus 操作技能
│   ├── SKILL.md                     # 精简版 - 消息服务
│   ├── references/
│   │   ├── core-concepts.md         # 命名空间、队列、主题、订阅、死信
│   │   ├── troubleshooting.md      # 死信、配额、消息延迟、连接断开
│   │   ├── aiops.md                # 死信积累、配额耗尽 RCA
│   │   └ integration.md             # SDK/CLI（SDK 方法已校验）
│   └ assets/
│       └ example-config.yaml       # 队列/主题/订阅示例
│
├── azure-eventhub-ops/              # Azure Event Hubs 操作技能
│   ├── SKILL.md                     # 精简版 - 事件流服务
│   ├── references/
│   │   ├── core-concepts.md         # 命名空间、事件中心、消费者组、TU/PU
│   │   ├── troubleshooting.md      # 节流、分区倾斜、消费者滞后
│   │   ├── aiops.md                # 吞吐节流、分区倾斜 RCA
│   │   └ integration.md             # SDK/CLI（SDK 方法已校验）
│   └ assets/
│       └ example-config.yaml       # Standard/Premium 命名空间示例
│
├── azure-backup-ops/                # Azure Backup (Recovery Services) 操作技能
│   ├── SKILL.md                     # 精简版 - 备份与还原
│   ├── references/
│   │   ├── cli-commands.md          # 全部 9 个操作的 CLI 命令
│   │   ├── core-concepts.md         # 保管库、保护、策略、还原点
│   │   ├── troubleshooting.md      # 备份失败、还原失败、保留策略
│   │   └ integration.md             # SDK/CLI、RBAC（SDK 方法已校验）
│   └ assets/
│       └ example-config.yaml       # VM/SQL DB 备份示例
│
├── azure-dns-ops/                   # Azure DNS Zones 操作技能
│   ├── SKILL.md                     # 精简版 - 公有与私有 DNS
│   ├── references/
│   │   ├── core-concepts.md         # 区域类型、记录类型、别名、委派
│   │   ├── troubleshooting.md      # 解析失败、委派错误、TTL 缓存
│   │   └ integration.md             # SDK/CLI（SDK 方法已校验）
│   └ assets/
│       └ example-config.yaml       # 公有/私有区域示例
│
├── azure-file-storage-ops/          # Azure File Storage 操作技能
│   ├── SKILL.md                     # 精简版 - SMB/NFS 文件共享
│   ├── references/
│   │   ├── core-concepts.md         # 共享、快照、软删除、配额、同步
│   │   ├── troubleshooting.md      # 挂载失败、权限、配额、同步冲突
│   │   └ integration.md             # SDK/CLI（SDK 方法已校验）
│   └ assets/
│       └ example-config.yaml       # 文件共享创建/恢复示例
│
├── azure-queue-storage-ops/         # Azure Queue Storage 操作技能
│   ├── SKILL.md                     # 精简版 - 消息队列
│   ├── references/
│   │   ├── commands.md              # CLI + SDK 命令参考
│   │   ├── core-concepts.md         # 队列、消息 TTL、SAS、毒消息
│   │   ├── troubleshooting.md      # 消息失败、超时、认证
│   │   └ integration.md             # SDK/CLI（SDK 方法已校验）
│   └ assets/
│       └ example-config.yaml       # 队列/消息示例
│
├── azure-site-recovery-ops/         # Azure Site Recovery 操作技能
│   ├── SKILL.md                     # 精简版 - 灾难恢复
│   ├── references/
│   │   ├── core-concepts.md         # 保管库、保护、故障转移、恢复计划
│   │   ├── troubleshooting.md      # 复制健康、故障转移失败
│   │   └ integration.md             # SDK/CLI（SDK 方法已校验）
│   └ assets/
│       └ example-config.yaml       # DR 配置示例
│
├── azure-eventgrid-ops/             # Azure Event Grid 操作技能
│   ├── SKILL.md                     # 精简版 - 事件路由服务
│   ├── references/
│   │   ├── core-concepts.md         # 主题、系统主题、事件订阅、过滤器
│   │   ├── troubleshooting.md      # 投递失败、死信、过滤错误
│   │   └ integration.md             # SDK/CLI（SDK 方法已校验）
│   └ assets/
│       └ example-config.yaml       # 主题/订阅示例
│
├── azure-apim-ops/                  # Azure API Management 操作技能
│   ├── SKILL.md                     # 精简版 - API 网关服务
│   ├── references/
│   │   ├── core-concepts.md         # 服务、SKU、API、产品、订阅、策略
│   │   ├── troubleshooting.md      # 网关故障、策略错误、订阅密钥
│   │   └ integration.md             # SDK/CLI（订阅/策略 CLI gap 已文档化）
│   └ assets/
│       └ example-config.yaml       # 服务/API/产品示例
│
└── azure-[service]-ops/             # 后续服务技能...
```

## 设计原则

### SKILL.md 精简
- 只关注 **What to do**: 触发条件、范围、执行流程概览
- ~100-150 行，Agent 可快速理解意图

### references 承载细节
- **How to do**: CLI 命令、SDK 代码、故障排查等
- 详细实现放在独立文件，按需加载

### 双路径执行
- **Primary**: Azure CLI (`az [service] [command]`)
- **Fallback**: Azure SDK for Python (CLI 失败后 3 次重试)

### 流程模式
```
Pre-flight → Execute → Validate → Recover
```

## 快速开始

### 使用 Meta Skill 生成新技能

当 Agent 加载 `azure-skill-generator` 后，提供以下信息：

```
Product: Azure [服务名]
Primary Resource: [资源类型]
Official Docs: https://docs.microsoft.com/azure/[service]/
CLI Support: az [service] --help
SDK Module: azure.mgmt.[service]
Operations: create, show, update, delete, list
```

Agent 将自动生成 `azure-[service]-ops` 目录结构。

### 使用现有技能

加载对应技能后，Agent 可执行：

```bash
# Load Balancer 示例
az network lb create --name my-lb --resource-group my-rg --location eastus --output json
az network lb show --name my-lb --resource-group my-rg --output json

# Application Gateway 示例
az network application-gateway create --name my-agw --resource-group my-rg --location eastus --output json
az network application-gateway show-backend-health --gateway-name my-agw --resource-group my-rg

# Front Door 示例
az afd profile create --profile-name my-fd --resource-group my-rg --sku Standard_AzureFrontDoor --output json
az afd endpoint create --endpoint-name my-endpoint --profile-name my-fd --resource-group my-rg

# Traffic Manager 示例
az network traffic-manager profile create --name my-tm --resource-group my-rg --routing-method Performance --output json
az network traffic-manager endpoint create --name endpoint-1 --profile-name my-tm --resource-group my-rg --type externalEndpoints --target myapp.azurewebsites.net

# Virtual Network 示例
az network vnet create --name my-vnet --resource-group my-rg --location eastus --address-prefixes 10.20.0.0/16 --subnet-name app-subnet --subnet-prefixes 10.20.1.0/24 --output json
az network vnet subnet list --vnet-name my-vnet --resource-group my-rg --output json

# App Service 示例
az appservice plan create --name my-plan --resource-group my-rg --location eastus --sku B1 --is-linux --output json
az webapp create --name my-webapp --resource-group my-rg --plan my-plan --runtime "PYTHON:3.11" --output json
```

## 环境设置

**前置要求**: Python >= 3.10

### 使用 .env 快速设置（推荐）

```bash
# 一次性设置：从 .env.example 复制 → .env 并生成配置
python azure-skill-generator/scripts/setup_env.py

# 编辑 .env 填入你的 Azure 凭证，然后重新渲染
python azure-skill-generator/scripts/setup_env.py --render

# 验证凭证是否有效
python azure-skill-generator/scripts/setup_env.py --check
```

这会生成 `azure-skill-generator/config.yaml`（包含你的实际凭证值），并解析模板文件中的 `{{env.*}}` 占位符。

### 手动设置

```bash
# 安装 Azure CLI
# macOS
brew install azure-cli

# Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# 创建 Service Principal 用于自动化
az ad sp create-for-rbac --name "my-automation-sp" --role "Contributor" --scopes "/subscriptions/{{env.AZURE_SUBSCRIPTION_ID}}" --output json

# 配置凭证
export AZURE_SUBSCRIPTION_ID="your_subscription_id"
export AZURE_TENANT_ID="your_tenant_id"
export AZURE_CLIENT_ID="your_client_id"
export AZURE_CLIENT_SECRET="your_client_secret"

# 验证
az account show --output json
```

## 已有技能

| 技能 | 服务 | 状态 |
|------|------|------|
| azure-cost-ops | Azure Cost Management (账单, 预算, 预留实例) | ✅ 完成 |
| azure-audit-ops | Azure Audit (操作日志, RBAC, 资源锁, 策略合规, 安全审计) | ✅ 完成 |
| azure-skill-generator | Meta Skill | ✅ 完成 |
| azure-vnet-ops | Virtual Network (VNet、子网、对等互连) | ✅ 完成 |
| azure-loadbalancer-ops | Load Balancer (L4 负载均衡) | ✅ 完成 |
| azure-nsg-ops | Network Security Group (NSG 规则与关联) | ✅ 完成 |
| azure-privateendpoint-ops | Private Endpoint (Private Link 与 DNS 集成) | ✅ 完成 |
| azure-appgateway-ops | Application Gateway (L7 + WAF) | ✅ 完成 |
| azure-frontdoor-ops | Front Door (全球加速 + CDN) | ✅ 完成 |
| azure-trafficmanager-ops | Traffic Manager (DNS 路由) | ✅ 完成 |
| azure-monitor-ops | Azure Monitor (指标/告警/日志) | ✅ 完成 |
| azure-aks-ops | Azure Kubernetes Service (AKS) | ✅ 完成 |
| azure-blobstorage-ops | Azure Blob Storage | ✅ 完成 |
| azure-vm-ops | Azure Virtual Machine | ✅ 完成 |
| azure-appservice-ops | Azure App Service (Web App、计划、槽位) | ✅ 完成 |
| azure-redis-ops | Azure Redis (缓存运维、AIOps、RCA) | ✅ 完成 |
| azure-postgres-ops | Azure PostgreSQL Flexible Server (数据库运维、AIOps、RCA) | ✅ 完成 |
| azure-acr-ops | Azure Container Registry (镜像运维、AIOps、RCA) | ✅ 完成 |
| azure-keyvault-ops | Azure Key Vault (Secret、Key、Certificate、AIOps、RCA) | ✅ 完成 |
| azure-sqldb-ops | Azure SQL 数据库（含弹性池） | ✅ 完成 |
| azure-function-ops | Azure Functions (Serverless 函数、双路径、GCL) | ✅ 完成 |
| azure-cosmos-ops | Azure Cosmos DB (RU/s、分区键、全局分布、GCL) | ✅ 完成 |
| azure-aci-ops | Azure Container Instances (Serverless 容器、GCL) | ✅ 完成 |
| azure-servicebus-ops | Azure Service Bus (队列/主题/订阅、GCL) | ✅ 完成 |
| azure-eventhub-ops | Azure Event Hubs (吞吐/捕获/自动膨胀、GCL) | ✅ 完成 |
| azure-backup-ops | Azure Backup (Recovery Services 保管库、GCL 强制) | ✅ 完成 |
| azure-dns-ops | Azure DNS Zones (公有/私有 DNS、GCL 强制) | ✅ 完成 |
| azure-file-storage-ops | Azure File Storage (SMB/NFS 文件共享、GCL 强制) | ✅ 完成 |
| azure-queue-storage-ops | Azure Queue Storage (消息队列、GCL 强制) | ✅ 完成 |
| azure-site-recovery-ops | Azure Site Recovery (容灾编排、GCL 强制) | ✅ 完成 |
| azure-eventgrid-ops | Azure Event Grid (主题/订阅、事件路由、GCL 强制) | ✅ 完成 |
| azure-apim-ops | Azure API Management (服务/API/产品/策略、GCL 强制) | ✅ 完成 |

## 计算服务对比

| 功能 | Virtual Machine | App Service | AKS | Container Instances |
|------|-----------------|-------------|-----|---------------------|
| **类型** | IaaS 完整服务器 | PaaS Web 托管 | 托管 Kubernetes | Serverless 容器 |
| **控制粒度** | 完整 OS 控制 | 托管运行时/平台 | 容器编排 | 单容器 |
| **扩缩容** | 手动/自动扩缩容 | 计划实例/SKU/自动缩放 | 集群自动缩放 | 手动扩缩容 |
| **持久化** | 持久磁盘 | 应用配置 + 挂载存储 | 持久卷 | 临时 |
| **适用场景** | 传统应用、完整控制 | Web 应用/API | 微服务、复杂应用 | 简单任务、批处理 |

## 存储服务对比

| 功能 | Blob Storage | File Storage | Disk Storage |
|------|--------------|--------------|--------------|
| **类型** | 对象存储 | SMB 文件共享 | 块存储 |
| **访问方式** | REST API/SAS | SMB/NFS 协议 | VM 挂载 |
| **规模** | 海量规模 (5 PB+) | 单共享限制 | 受 VM 限制 |
| **适用场景** | 文档、图片、备份 | 文件共享、迁移 | VM OS/数据磁盘 |

## 容器服务对比

| 功能 | AKS | Container Instances |
|------|-----|---------------------|
| **编排** | 完整 Kubernetes | 单容器 |
| **扩缩容** | 集群自动扩缩容 | 手动扩缩容 |
| **管理方式** | 托管 Kubernetes | Serverless 容器 |
| **适用场景** | 微服务、复杂应用 | 简单任务、批处理 |
| **集成** | ACR、Helm、Istio | ACR、简单部署 |

## 网络服务对比

| 功能 | Virtual Network | NSG | Private Endpoint | Load Balancer | App Gateway | Front Door | Traffic Manager |
|------|-----------------|-----|------------------|---------------|-------------|------------|-----------------|
| **层级** | 网络基础 | L3/L4 过滤 | Private Link 访问 | L4 (TCP/UDP) | L7 (HTTP/HTTPS) | L7 (HTTP/HTTPS) | DNS |
| **范围** | 单 Location / 对等 VNet | 子网/NIC | 子网到目标资源 | 单 Location | 单 Location | 全球 | 全球 |
| **主要用途** | 地址空间、子网、私有连接 | 允许/拒绝流量规则 | 私有服务连接 | VM/后端负载均衡 | Web 入口 + WAF | 全球加速 | DNS 故障转移/路由 |
| **管理子网** | 是 | 关联子网/NIC | 在子网分配私有 IP | 否 | 需要专用子网 | 否 | 否 |
| **破坏风险** | 影响附加资源 | 阻断或暴露流量 | 中断私有连接 | 流量中断 | 流量中断 | 全球流量影响 | DNS 路由影响 |

## 负载均衡服务对比

| 功能 | Load Balancer | App Gateway | Front Door | Traffic Manager |
|------|---------------|-------------|------------|-----------------|
| **层级** | L4 (TCP/UDP) | L7 (HTTP/HTTPS) | L7 (HTTP/HTTPS) | DNS |
| **范围** | 单区域 | 单区域 | 全球 | 全球 |
| **CDN** | 无 | 无 | 有 | 无 |
| **WAF** | 无 | 有 | Premium版有 | 无 |
| **SSL终止** | 无 | 有 | 有 | 在端点 |
| **URL路由** | 无 | 有 | 有 | 无 |
| **适用场景** | VM负载均衡 | Web应用 | 全球加速 | 故障转移/地理路由 |

## Azure vs AWS 对比

| 维度 | Azure | AWS |
|------|-------|-----|
| CLI工具 | `az` | `aws` |
| 主要SDK | Azure SDK for Python | boto3 |
| 认证方式 | Service Principal / Azure AD | IAM User / Role |
| 资源ID格式 | `/subscriptions/.../providers/...` | `arn:aws:...` |
| 区域术语 | **Location** | Region |
| 容器概念 | **Resource Group** (必需) | 无等效概念 |
| L4负载均衡 | Load Balancer | ELB (NLB/CLB) |
| L7负载均衡 | Application Gateway | ELB (ALB) |
| 全球负载均衡 | Front Door | CloudFront (CDN) + Route 53 |
| DNS负载均衡 | Traffic Manager | Route 53 |

## 参考

- [Azure CLI 文档](https://docs.microsoft.com/cli/azure/)
- [Azure SDK for Python](https://docs.microsoft.com/python/api/overview/azure/)
- [Azure REST API 参考](https://docs.microsoft.com/rest/api/azure/)
- [Agent Skills OpenSpec](https://agentskills.io/specification)

## License

MIT