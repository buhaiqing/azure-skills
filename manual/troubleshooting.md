---
title: 故障排查
description: 常见问题与解决方案
---

# 故障排查

## 1. LLM Critic 返回格式错误

**症状**：
```
AttributeError: 'dict' object has no attribute 'scores'
```

**解决**：
```bash
# 检查 API key
echo $DASHSCOPE_API_KEY

# 测试连接
python -c "from llm_critic import CriticModel; m = CriticModel(); print(m.provider)"

# 回退到规则评分
python scripts/gcl_runner.py --critic rule ...
```

## 2. 一直 Escalate

**排查步骤**：

```bash
# 1. 检查 az 命令
az vm show --name my-vm --resource-group my-rg

# 2. 检查 desired_state 字段
python scripts/auto_feedback_loop.py \
  --desired-state '{"powerState": "VM running"}'  # 正确

# 3. 查看 trace
cat audit-results/gcl-trace-xxx.json | jq .

# 4. 验证 JSON 格式
jq '.powerState' <(az vm show ...)
```

## 3. 编排引擎找不到依赖

```bash
# 检查依赖图
python scripts/orchestrator.py --list-deps azure-aks-ops

# 验证依赖图文件
cat scripts/dependency_graph.json | jq '.nodes | length'
```

## 4. 记忆层推荐不准确

```python
from scripts.memory.memory_store import MemoryStore

store = MemoryStore()

# 清理过时记录
deleted = store.prune(max_age_days=30, min_success_rate=0.5)
print(f"清理了 {deleted} 条记录")

# 查看统计
stats = store.stats()
print(f"总记录数: {stats['total_entries']}")
```

## 5. Mock 场景全部失败

```bash
# 检查 Mock 类
python -c "from scripts.mock_azure import MockAzure; m = MockAzure(); print(m.execute('az vm list'))"

# 验证场景文件
python -c "import json; json.load(open('scripts/mock_azure_scenarios/azure-vm-ops.json'))"
```

## 6. Trace 分析

```bash
# 列出最近的 trace
ls -lt audit-results/ | head -5

# 分析特定 trace
cat audit-results/gcl-trace-xxx.json | python -m json.tool

# 提取关键信息
cat audit-results/gcl-trace-xxx.json | jq '{
  status: .metadata.status,
  skill: .metadata.skill,
  heal_attempts: .metadata.heal_attempts
}'
```

## 7. 日志级别

```bash
# 默认：INFO
python scripts/auto_feedback_loop.py ...

# Verbose：DEBUG
VERBOSE=true python scripts/auto_feedback_loop.py ...

# Silent：只输出结果
SILENT=true python scripts/auto_feedback_loop.py ...
```
