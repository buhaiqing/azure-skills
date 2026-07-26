---
title: 最佳实践
description: azure-skills 开发和使用的推荐模式
---

# 最佳实践

## 1. desired_state 设计

### ✅ 推荐：使用稳定的字段

```python
desired_state = {"powerState": "VM running"}
desired_state = {"provisioningState": "Succeeded"}
```

### ❌ 避免：使用可能变化的字段

```python
desired_state = {"vmId": "xxx"}  # VM ID 可能变化
desired_state = {"Name": "my-vm"}  # 仅检查名称，不验证状态
```

## 2. 自愈策略设计

### ✅ 推荐：设置合理的超时和重试

```json
{
  "max_attempts": 3,
  "backoff_seconds": 30,
  "timeout_seconds": 300
}
```

### ❌ 避免：无限制重试

```json
{
  "max_attempts": 999,  // 可能导致死循环
  "backoff_seconds": 0
}
```

### ✅ 推荐：分阶段修复

```json
{
  "healing_rules": [
    {"action": "vm_start", "max_attempts": 2},
    {"action": "vm_restart", "max_attempts": 1},
    {"action": "redeploy", "max_attempts": 1}
  ]
}
```

## 3. LLM Critic 使用

### ✅ 推荐：设置合理的阈值

```python
rubric = {
    "correctness": {"threshold": 0.5},
    "safety": {"threshold": 1.0},  # 必须完全安全
    "idempotency": {"threshold": 0.5},
    "traceability": {"threshold": 0.5},
    "spec_compliance": {"threshold": 0.5}
}
```

### ❌ 避免：阈值过低

```python
rubric = {"safety": {"threshold": 0.0}}  # 允许不安全操作
```

## 4. 记忆层使用

### ✅ 推荐：记录丰富的 metadata

```python
store.record(
    skill="azure-vm-ops",
    symptom="vm_not_starting",
    strategy="vm_start",
    success=True,
    metadata={
        "resource_group": "my-rg",
        "error_code": "VmStartTimedOut",
        "vm_size": "Standard_D2s_v3"
    }
)
```

### ✅ 推荐：定期清理

```python
store.prune(max_age_days=30, min_success_rate=0.5)
```

### ✅ 推荐：跨技能迁移

```python
store.transfer(
    from_skill="azure-vm-ops",
    to_skill="azure-aks-ops",
    symptom_mapping={"vm_not_starting": "node_not_ready"},
    min_success_rate=0.6
)
```

## 5. 性能优化

### ✅ 推荐：复用 Orchestrator 实例

```python
orch = Orchestrator()  # 一次初始化
for symptom in symptoms:
    result = orch.diagnose(symptom)  # 复用
```

### ✅ 推荐：批量记录记忆

```python
store.batch_record([
    {"skill": "azure-vm-ops", "symptom": "vm_not_starting", "strategy": "vm_start", "success": True},
    {"skill": "azure-vm-ops", "symptom": "vm_unresponsive", "strategy": "vm_restart", "success": True},
])
```

## 6. 安全建议

1. **destructive 操作必须人工确认** - 不要设置 `--risky` 标志
2. **定期轮换凭据** - 建议 90 天轮换一次
3. **使用最小权限** - Service Principal 只授予必要权限
4. **不要提交 .env** - `.gitignore` 已忽略，确保不提交

## 7. 监控建议

1. **定期查看健康仪表板** - `python scripts/health_dashboard.py`
2. **关注 escalation 率** - 高于 15% 需要调查
3. **定期清理记忆层** - 保持推荐准确性
4. **保存 trace** - 便于事后分析
