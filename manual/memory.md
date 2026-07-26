---
title: 执行记忆层
description: memory_store.py 经验持久化与推荐
---

# 执行记忆层

> 记住历史执行结果，下次同类场景推荐最优策略。

## 1. 核心概念

```
Memory Store 基于 (skill, symptom, strategy) → success_rate 的映射
```

## 2. Python API

```python
from scripts.memory.memory_store import MemoryStore

store = MemoryStore(storage_dir=".runtime/memory/")
```

### 记录执行结果

```python
store.record(
    skill="azure-vm-ops",
    symptom="vm_not_starting",
    strategy="vm_start",
    success=True,
    duration_seconds=45.2,
    metadata={
        "resource_group": "my-rg",
        "error_before": "VmStartTimedOut"
    }
)
```

### 推荐最优策略

```python
best = store.recommend(
    skill="azure-vm-ops",
    symptom="vm_not_starting",
    top_k=3
)
print(best)
# [
#   {"strategy": "vm_start", "success_rate": 0.85, "total_attempts": 20},
#   {"strategy": "vm_restart", "success_rate": 0.72, "total_attempts": 15},
#   {"strategy": "redeploy", "success_rate": 0.45, "total_attempts": 8}
# ]
```

### 跨技能经验迁移

```python
# VM 的修复经验迁移到 AKS Node
store.transfer(
    from_skill="azure-vm-ops",
    to_skill="azure-aks-ops",
    symptom_mapping={
        "vm_not_starting": "node_not_ready",
        "vm_stopped": "node_down"
    },
    min_success_rate=0.6
)
```

### 清理过时记录

```python
# 删除：30 天未使用 或 成功率 < 50%
deleted = store.prune(max_age_days=30, min_success_rate=0.5)
print(f"清理了 {deleted} 条记录")
```

### 统计信息

```python
stats = store.stats()
print(stats)
# {
#   "total_entries": 142,
#   "unique_skills": 31,
#   "unique_symptoms": 58,
#   "unique_strategies": 89,
#   "avg_success_rate": 0.72
# }
```

## 3. 记忆衰减机制

| 条件 | 动作 |
|------|------|
| 30 天内未使用 | 标记 `deprecated` |
| 成功率 < 50% | 标记 `deprecated` |
| 两者都满足 | 立即删除 |

## 4. 存储格式

纯 JSONL，位于 `.runtime/memory/`：

```bash
ls .runtime/memory/
# memory_2026-07.jsonl
# memory_2026-08.jsonl
```

**每行格式**：

```jsonl
{"skill": "azure-vm-ops", "symptom": "vm_not_starting", "strategy": "vm_start", "success": true, "timestamp": "2026-07-18T10:30:00Z", "duration_seconds": 45.2}
```
