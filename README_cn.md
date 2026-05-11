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

├── azure-loadbalancer-ops/          # Load Balancer 操作技能
│   ├── SKILL.md                     # 精简版 - L4 负载均衡
│   ├── references/
│   │   ├── core-concepts.md         # 负载均衡器类型、SKU
│   │   ├── troubleshooting.md      # 后端池、健康探测问题
│   │   └ integration.md             # Service Principal 设置
│   └ assets/
│       └ example-config.yaml       # 公网/内网负载均衡器示例

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
az ad sp create-for-rbac --name "my-automation-sp" --role "Contributor" --scopes "/subscriptions/{{subscription-id}}" --output json

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
| azure-skill-generator | Meta Skill | ✅ 完成 |
| azure-loadbalancer-ops | Load Balancer (L4 负载均衡) | ✅ 完成 |
| azure-appgateway-ops | Application Gateway (L7 + WAF) | ✅ 完成 |
| azure-frontdoor-ops | Front Door (全球加速 + CDN) | ✅ 完成 |
| azure-trafficmanager-ops | Traffic Manager (DNS 路由) | ✅ 完成 |
| azure-monitor-ops | Azure Monitor (指标/告警/日志) | ✅ 完成 |

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