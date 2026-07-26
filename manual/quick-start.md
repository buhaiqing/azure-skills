---
title: 快速入门
description: 5 分钟上手 azure-skills L4 自动化
---

# 快速入门

> 5 分钟内完成环境配置并运行第一个 L4 闭环。

## 前置要求

- Python 3.10+
- Azure 订阅
- Git

## 步骤 1：克隆并进入目录

```bash
git clone https://github.com/buhaiqing/azure-skills.git
cd azure-skills
```

## 步骤 2：配置环境变量

```bash
# 复制模板
cp .env.example .env

# 编辑 .env，填入你的 Azure 凭据
vim .env
```

**`.env` 最小配置**：

```bash
# Azure 服务主体
AZURE_SUBSCRIPTION_ID=your_subscription_id
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret

# 可选：LLM Critic（用于语义审核）
DASHSCOPE_API_KEY=sk-xxx
```

> **Azure 凭据获取**：
> ```bash
> az ad sp create-for-rbac --name "azure-skills" --role "Contributor" \
>   --scopes "/subscriptions/your_subscription_id"
> ```

## 步骤 3：验证配置

```bash
# 验证 Azure 登录
az account show

# 验证 Python 环境
python3 --version  # 需要 3.10+
```

## 步骤 4：运行第一个 L4 闭环

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-vm-ops \
  --operation vm_create \
  --command "az vm create \
    --name my-first-vm \
    --resource-group my-rg \
    --image UbuntuLTS \
    --admin-username azureuser \
    --admin-password 'YourPassword123!'" \
  --desired-state '{"powerState": "VM running"}'
```

**预期输出**：

```
[INFO] Executing: az vm create ...
[INFO] Observing state...
[INFO] Diff: desired={"powerState": "VM running"} vs actual={"powerState": "VM running"}
[INFO] Status: success
```

## 步骤 5：查看健康状态

```bash
python scripts/health_dashboard.py
```

**预期输出**：

```
══════════════════════════════════════════════════
          Azure Skills L4 Health
══════════════════════════════════════════════════

L4 Certification Targets:
  ✓ Safety Pass Rate:      100%
  ✓ Auto-Heal Success:     93%
  ✓ Escalation Rate:         6%
```

## 常见操作示例

### 创建 AKS 集群并等待就绪

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-aks-ops \
  --operation aks_create \
  --command "az aks create \
    --name my-cluster \
    --resource-group my-rg \
    --node-count 3 \
    --generate-ssh-keys" \
  --desired-state '{"provisioningState": "Succeeded"}'
```

### 上传 Blob 并验证

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-blobstorage-ops \
  --operation blob_upload \
  --command "az storage blob upload \
    --account-name mystorage \
    --container-name mycontainer \
    --name myblob.txt \
    --file ./myblob.txt" \
  --desired-state '{"name": "myblob.txt"}'
```

### 使用 LLM Critic 评分

```bash
export DASHSCOPE_API_KEY=sk-xxx

python scripts/gcl_runner.py \
  --skill azure-vm-ops \
  --critic llm \
  --request "az vm list --resource-group my-rg"
```

### 诊断跨服务问题

```bash
python scripts/orchestrator.py \
  --diagnose "AKS node not ready"
```

**输出示例**：

```
诊断：AKS node not ready
─────────────────────────────────────
依赖链 (BFS):
  [L0] azure-aks-ops
  [L1] azure-vm-ops → azure-vnet-ops → azure-nsg-ops

建议检查顺序：
  1. azure-vm-ops: 检查节点状态
  2. azure-nsg-ops: 检查 NSG 规则
  3. azure-vnet-ops: 检查子网配置
```

## 下一步

| 任务 | 文档 |
|------|------|
| 理解架构 | [系统架构](./architecture.md) |
| 完整 API | [L4 闭环](./l4闭环.md) |
| 配置更多服务 | [环境配置](./configuration.md) |
| 故障排查 | [故障排查](./troubleshooting.md) |

## 常见问题

### Q: 一直返回 escalated？

检查 `desired_state` 字段是否正确：

```bash
# 查看资源实际状态
az vm show --name my-vm --resource-group my-rg --output json | jq '.powerState'
```

### Q: LLM Critic 返回错误？

```bash
# 检查 API key
echo $DASHSCOPE_API_KEY

# 使用规则评分作为替代
python scripts/gcl_runner.py --skill azure-vm-ops --critic rule ...
```

### Q: 没有 Azure 订阅？

使用 Mock 验证：

```bash
python scripts/run_all_scenarios.py
```
