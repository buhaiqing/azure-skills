---
title: 扩展指南
description: 添加新 Skill 和自定义功能
---

# 扩展指南

## 1. 添加新 Skill

### 步骤 1：创建自愈策略文件

```bash
cp scripts/self_healing/azure-vm-ops.json scripts/self_healing/azure-my-service-ops.json
```

### 步骤 2：编辑策略文件

```json
{
  "skill": "azure-my-service-ops",
  "operations": {
    "my_operation": {
      "risky": false,
      "health_check": {
        "api": "az my-service show",
        "parse_field": "provisioningState",
        "expected": "Succeeded"
      },
      "healing_rules": [
        {
          "condition_type": "field_not_equal",
          "condition_field": "provisioningState",
          "condition_value": "Succeeded",
          "heal_action": "az my-service wait",
          "max_attempts": 4,
          "backoff_seconds": 30
        }
      ]
    }
  }
}
```

### 步骤 3：验证策略

```bash
python scripts/self_healing/validate.py --skill azure-my-service-ops
```

### 步骤 4：创建 Mock 场景

```bash
cat > scripts/mock_azure_scenarios/azure-my-service-ops.json << 'EOF'
{
  "skill": "azure-my-service-ops",
  "scenarios": [
    {
      "name": "operation_success",
      "description": "操作成功",
      "command": "az my-service create --name my-service --resource-group my-rg",
      "expected_exit_code": 0,
      "expected_state": {"provisioningState": "Succeeded"}
    }
  ]
}
EOF
```

### 步骤 5：测试

```bash
python scripts/run_all_scenarios.py --skill azure-my-service-ops
```

---

## 2. 自定义 LLM Prompt

```python
from llm_critic import CriticModel

model = CriticModel(provider='qwen')

custom_prompt = """
你是一个专业的 Azure CLI 审核员。
请评估以下命令执行结果是否符合规范。
"""

result = model.score(
    generator_output,
    rubric,
    trace,
    system_prompt=custom_prompt
)
```

---

## 3. 自定义指标上报

```python
from scripts.health_dashboard import HealthDashboard

class MyDashboard(HealthDashboard):
    def collect_custom_metrics(self):
        self.custom_metrics.append({
            "name": "my_custom_metric",
            "value": 42,
            "unit": "Count"
        })
        return self.custom_metrics

dashboard = MyDashboard()
dashboard.report()
```

---

## 4. 集成到现有系统

### 作为 Python 包导入

```python
from scripts import auto_feedback_loop, llm_critic, orchestrator

result = auto_feedback_loop.run_with_feedback(...)
```

### 作为 HTTP 服务运行

```bash
python -m scripts.auto_feedback_loop --serve --port 8080

# API: POST /feedback
curl -X POST http://localhost:8080/feedback \
  -H "Content-Type: application/json" \
  -d '{"skill": "azure-vm-ops", "operation": "vm_create", ...}'
```

---

## 5. 扩展依赖图

```bash
vim scripts/dependency_graph.json
```

添加新节点和边：

```json
{
  "nodes": [
    {"id": "azure-my-service-ops", "label": "My Service"}
  ],
  "edges": [
    {"from": "azure-my-service-ops", "to": "azure-vnet-ops", "type": "depends_on"}
  ]
}
```

---

## 6. 贡献指南

1. Fork 仓库
2. 创建功能分支
3. 添加测试
4. 运行 Mock 测试
5. 提交 PR

```bash
# 运行所有测试
python scripts/run_all_scenarios.py

# 运行单元测试
pytest tests/
```
