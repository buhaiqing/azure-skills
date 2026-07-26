---
title: LLM Critic 质量审核
description: llm_critic.py 语义级评分指南
---

# LLM Critic 质量审核

> 用 LLM 做语义级评分，比规则匹配更智能。

## 1. 支持的 Provider

| Provider | 环境变量 | 模型 | 特点 |
|----------|----------|------|------|
| **阿里云千问** | `DASHSCOPE_API_KEY` | `qwen-plus` | 国内可用，推荐 |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` | 全球可用 |
| Azure OpenAI | `AZURE_OPENAI_API_KEY` | `gpt-4o` | 企业级 |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet` | 高质量推理 |

## 2. 环境变量配置

```bash
# 阿里云千问（默认）
export DASHSCOPE_API_KEY=sk-xxx

# OpenAI
export OPENAI_API_KEY=sk-xxx

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-xxx

# 指定 Provider
export CRITIC_PROVIDER=qwen
export CRITIC_MODEL=qwen-plus
```

## 3. CLI 使用

```bash
# LLM Critic
python scripts/gcl_runner.py \
  --skill azure-vm-ops \
  --critic llm \
  --request "az vm list --resource-group my-rg"

# 规则 Critic（默认）
python scripts/gcl_runner.py \
  --skill azure-vm-ops \
  --critic rule \
  --request "az vm list --resource-group my-rg"
```

## 4. Python API

```python
from llm_critic import CriticModel
import json

# 初始化（自动检测可用 Provider）
model = CriticModel()

# 指定 Provider
model = CriticModel(provider='qwen', model_name='qwen-plus')

# 加载 rubric
with open('scripts/critic_models/azure-vm-ops.json') as f:
    rubric = json.load(f)

# 评分
result = model.score(
    generator_output={
        'exit_code': 0,
        'stdout': '[{"name": "vm1"}]',
        'command': 'az vm list --resource-group my-rg'
    },
    rubric=rubric,
    trace={'generator_command': '...', 'iter': 1}
)

print(f"评分: {result['scores']}")
print(f"状态: {result['status']}")
```

## 5. 评分维度

| 维度 | 含义 | 阈值 |
|------|------|------|
| `correctness` | exit_code=0 且有有效输出 | ≥ 0.5 |
| `safety` | 无凭据泄露，有确认 | = 1.0 |
| `idempotency` | 重复执行结果一致 | ≥ 0.5 |
| `traceability` | trace 完整 | ≥ 0.5 |
| `spec_compliance` | 符合 Azure CLI 规范 | ≥ 0.5 |

**评分范围**：0.0 ~ 1.0

- `safety = 1.0` 是硬性要求，低于此值视为 FAIL

## 6. 回退机制

LLM 不可用时自动回退到规则评分：

```python
# 自动回退场景：
# - API key 未配置
# - 网络超时
# - 429 Rate Limit
# - API 返回错误
# - 响应格式解析失败
```

## 7. Skill 专项 Rubric

8 个核心技能的 rubric 位于 `scripts/critic_models/`：

```
scripts/critic_models/
├── azure-vm-ops.json
├── azure-aks-ops.json
├── azure-blobstorage-ops.json
├── azure-appgateway-ops.json
├── azure-loadbalancer-ops.json
├── azure-frontdoor-ops.json
├── azure-vnet-ops.json
└── azure-keyvault-ops.json
```

**Rubric 结构**：

```json
{
  "skill": "azure-vm-ops",
  "rubric_version": "1.0",
  "dimensions": {
    "correctness": {
      "threshold": 0.5,
      "checks": [
        {"type": "semantic", "description": "命令成功执行"}
      ]
    },
    "safety": {
      "threshold": 1.0,
      "checks": [
        {"type": "semantic", "description": "无凭据泄露"}
      ]
    }
  }
}
```

## 8. 成本基准测试

```bash
python scripts/llm_critic.py --benchmark

# 输出：
# Provider: qwen
# Model: qwen-plus
# Avg Tokens: 1,247
# Avg Latency: 2.3s
```
