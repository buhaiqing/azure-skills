---
title: 环境变量配置
description: 所有环境变量完整说明
---

# 环境变量配置

## 1. 完整配置清单

### Azure 凭据（必需）

```bash
# 服务主体（推荐用于自动化）
export AZURE_SUBSCRIPTION_ID=your_subscription_id
export AZURE_TENANT_ID=your_tenant_id
export AZURE_CLIENT_ID=your_client_id
export AZURE_CLIENT_SECRET=your_client_secret

# 或使用 Azure CLI
az login
```

### LLM Critic（可选）

```bash
# 阿里云千问（推荐，国内可用）
export DASHSCOPE_API_KEY=sk-xxx

# OpenAI
export OPENAI_API_KEY=sk-xxx

# Azure OpenAI
export AZURE_OPENAI_API_KEY=xxx
export AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-xxx

# 指定 Provider（可选）
export CRITIC_PROVIDER=qwen  # openai | azure_openai | anthropic
export CRITIC_MODEL=qwen-plus
```

### Azure Monitor（可选）

```bash
export AZURE_SUBSCRIPTION_ID=xxx
export AZURE_APP_INSIGHTS_RESOURCE_ID=/subscriptions/xxx/.../applicationinsights/xxx
```

### 其他配置

```bash
export AZURE_DEFAULT_LOCATION=eastus
export AZURE_CLI_OUTPUT=json
export SKILL_GEN_VERBOSE=false
```

## 2. 凭证优先级

```
1. Shell 环境变量（最高）
2. .env 文件
3. Azure CLI 默认
4. Managed Identity
```

## 3. 多环境配置

```bash
# .env.dev
AZURE_SUBSCRIPTION_ID=dev-sub-id

# .env.prod
AZURE_SUBSCRIPTION_ID=prod-sub-id

# 使用
export $(cat .env.prod | xargs)
```
