---
title: Mock 验证
description: mock_azure.py 无需真实 Azure 订阅即可测试
---

# Mock 验证

> 无需真实 Azure 订阅，在本地测试 L4 闭环。

## 1. 为什么需要 Mock

```
传统验证：需要 Azure 订阅，受限于成本和权限
Mock 验证：本地无限测试，无成本
```

## 2. MockAzure 类

```python
from scripts.mock_azure import MockAzure

mock = MockAzure()

# 模拟 VM 创建
result = mock.execute("az vm create --name my-vm --resource-group my-rg --image UbuntuLTS")
# {"exit_code": 0, "stdout": '{"name": "my-vm", "provisioningState": "Succeeded"}'}

# 模拟错误
mock.set_failure_mode("vm_create", error="VmCreationFailed")
result = mock.execute("az vm create ...")
# {"exit_code": 1, "stderr": "ERROR: VmCreationFailed"}
```

## 3. 运行场景

```bash
# 运行所有场景
python scripts/run_all_scenarios.py

# 运行特定技能
python scripts/run_all_scenarios.py --skill azure-vm-ops

# 指定场景
python scripts/run_all_scenarios.py --skill azure-vm-ops --scenario vm_create_success

# 详细输出
python scripts/run_all_scenarios.py --verbose
```

## 4. 输出示例

```
══════════════════════════════════════════════════
          Mock Azure Test Results
══════════════════════════════════════════════════

Total: 24 scenarios
Passed: 24 (100%)
Failed: 0 (0%)

By Skill:
  ✓ azure-vm-ops:          3/3
  ✓ azure-aks-ops:          3/3
  ✓ azure-blobstorage-ops:  3/3
  ...
```

## 5. 场景文件格式

每个 skill 有 3 个场景（正常/异常/边界）：

```json
{
  "skill": "azure-vm-ops",
  "scenarios": [
    {
      "name": "vm_create_success",
      "description": "VM 创建成功",
      "command": "az vm create ...",
      "expected_exit_code": 0,
      "expected_state": {"provisioningState": "Succeeded", "powerState": "VM running"}
    },
    {
      "name": "vm_create_timeout",
      "description": "VM 创建超时",
      "command": "az vm create ...",
      "expected_exit_code": 0,
      "expected_state": {"provisioningState": "Creating"},
      "heal_expected": "az vm start"
    },
    {
      "name": "vm_create_failed",
      "description": "VM 创建失败",
      "command": "az vm create ...",
      "expected_exit_code": 1,
      "expected_state": {"provisioningState": "Failed"},
      "heal_expected": "escalate"
    }
  ]
}
```

## 6. 场景文件位置

```
scripts/mock_azure_scenarios/
├── azure-vm-ops.json
├── azure-aks-ops.json
├── azure-blobstorage-ops.json
├── azure-appgateway-ops.json
├── azure-loadbalancer-ops.json
├── azure-frontdoor-ops.json
├── azure-vnet-ops.json
└── azure-keyvault-ops.json
```
