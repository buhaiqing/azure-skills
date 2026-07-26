# LLM Critic vs Rule-based Critic 对比报告

> 生成日期: 2026-07-26
> 环境: macOS, Python 3.12.1
> LLM Provider: 未配置（fallback 到 rule-based）

## 测试方法

对 8 个核心 Azure 技能，每个技能在 `--critic llm` 和 `--critic rule` 两种模式下
运行 GCL dry-run，记录评分结果。

由于当前环境未配置 LLM API key，`--critic llm` 模式自动 fallback 到 rule-based 评分，
因此当前 LLM vs Rule 评分结果一致。本报告框架设计为可重复运行，配置 API key 后
即可产出真实差异数据。

## 测试命令

```bash
python scripts/gcl_runner.py <skill> --critic llm --dry-run -- '<az command>'
python scripts/gcl_runner.py <skill> --critic rule --dry-run -- '<az command>'
```

## 测试结果

| 技能 | LLM Critic 结果 | Rule Critic 结果 | 差异 |
|------|----------------|------------------|------|
| azure-vm-ops | PASS (iter=1) | PASS (iter=1) | 相同（LLM fallback 到 rule-based） |
| azure-aks-ops | PASS (iter=1) | PASS (iter=1) | 相同 |
| azure-blobstorage-ops | PASS (iter=1) | PASS (iter=1) | 相同 |
| azure-appgateway-ops | PASS (iter=1) | PASS (iter=1) | 相同 |
| azure-loadbalancer-ops | PASS (iter=1) | PASS (iter=1) | 相同 |
| azure-frontdoor-ops | PASS (iter=1) | PASS (iter=1) | 相同 |
| azure-keyvault-ops | PASS (iter=1) | PASS (iter=1) | 相同 |
| azure-vnet-ops | PASS (iter=1) | PASS (iter=1) | 相同 |

## 评分维度明细（以 azure-vm-ops 为例）

| 维度 | LLM Critic | Rule Critic | 差异 |
|------|-----------|-------------|------|
| correctness | 1.0 | 1.0 | 相同 |
| safety | 1.0 | 1.0 | 相同 |
| idempotency | 1.0 | 1.0 | 相同 |
| traceability | 1.0 | 1.0 | 相同 |
| spec_compliance | 1.0 | 1.0 | 相同 |

## 已知限制

1. **API Key 缺失**：当前未配置 `OPENAI_API_KEY` / `AZURE_OPENAI_API_KEY` / `ANTHROPIC_API_KEY`，
   LLM Critic 自动 fallback 到 rule-based。配置 API key 后重新运行可获取真实对比数据。
2. **Dry-run 模式**：所有测试使用 mock generator 输出，未在真实 Azure 环境执行。
3. **测试命令**：每个技能使用统一的 mock 命令格式 `az <service> show --name test --resource-group test-rg --output json`。

## 后续步骤

配置 API key 后运行以下命令获取真实对比：

```bash
# 设置 API key
export OPENAI_API_KEY="sk-..."

# 运行完整对比测试
for skill in azure-vm-ops azure-aks-ops azure-blobstorage-ops \
             azure-appgateway-ops azure-loadbalancer-ops \
             azure-frontdoor-ops azure-keyvault-ops azure-vnet-ops; do
  python scripts/gcl_runner.py "$skill" --critic llm --dry-run -- 'az <svc> show --output json'
done
```

对比报告将更新为 LLM 实际评分 vs rule-based 评分的差异分析。
