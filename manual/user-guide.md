# 用户指南

> `auto_feedback_loop.py` 和 `gcl_runner.py` 的完整说明

---

## 决策树：何时用哪个工具

```
执行 Azure 操作
     │
     ▼
是否 destructive（delete / stop / purge / scale-to-zero）？
     YES → 走 SKILL.md Safety Gate，必须人工确认
     NO  ▼
     │
     ▼
有 desired_state 吗？
     YES → auto_feedback_loop.py（L4 闭环，自动修复）
     NO  ▼
     │
     ▼
需要量化质量评分？
     YES → gcl_runner.py（GCL 评分）
     NO  → 直接执行 az 命令
```

---

## `auto_feedback_loop.py` — L4 自动化闭环

### 函数签名

```python
def run_with_feedback(
    skill: str,                  # e.g. "azure-vm-ops"
    operation: str,              # e.g. "vm_create"
    command: str,                # 原始 az 命令字符串
    desired_state: dict,         # 期望状态字典
    risky: bool = False,         # True = 强制跳过闭环
    max_heal_attempts: int = 2, # 最大修复尝试次数
    trace_id: str | None = None,
    dry_run: bool = False,
) -> FeedbackResult
```

### desired_state 怎么写

`desired_state` 是你要的**资源最终状态**。格式是 JSON，支持 JMESPath 路径。

| 资源 | 字段 | 示例值 |
|------|------|--------|
| VM | `statuses[1].displayStatus` | `"VM running"` |
| AKS | `provisioningState` | `"Succeeded"` |
| Blob Container | `name` | `"my-container"` |
| DNS Zone | `provisioningState` | `"Succeeded"` |
| Key Vault | `properties.provisioningState` | `"Succeeded"` |
| App Service | `state` | `"Running"` |

**示例：**

```python
# VM running
desired_state={"statuses[1].displayStatus": "VM running"}

# AKS cluster ready
desired_state={"provisioningState": "Succeeded"}

# Blob container exists
desired_state={"name": "my-container"}
```

### 返回值：FeedbackResult

```python
@dataclass
class FeedbackResult:
    status: str           # "success" | "healed" | "escalated" | "failed"
    actual_state: dict   # Azure API 返回的原始状态
    heal_attempts: int   # 实际尝试修复次数
    trace_id: str        # 关联 trace ID
    message: str         # 人类可读摘要
    escalation: str|None  # 升人工消息（有的话）
```

### status 含义

| status | 含义 | 你该做什么 |
|--------|------|-----------|
| `success` | 操作执行 + 状态比对一致 | 无需操作 |
| `healed` | 执行后状态不对，但自动修复成功了 | 检查结果是否符合预期 |
| `escalated` | 自动修复不了，已升人工 | 看 `escalation` 消息，按建议处理 |
| `failed` | 命令执行本身失败（如参数错误）| 修复命令后重试 |

### 补偿策略（healing）

补偿策略由 `scripts/self_healing/*.json` 定义，不同操作有不同策略：

| 操作 | 补偿动作 | 最多尝试 |
|------|---------|---------|
| VM 创建后非 running | `az vm start` | 2 次 |
| AKS 创建后未就绪 | `az aks wait` | 4 次 |
| Key Vault 创建后未就绪 | `az keyvault show` 轮询 | 4 次 |
| App Service 创建后未 running | `az webapp start` | 2 次 |
| 其余操作 | 升人工 | — |

---

## `gcl_runner.py` — GCL 质量门

### 函数签名

```python
def orchestrate(
    skill: str,           # e.g. "azure-vm-ops"
    user_request: str,     # 原始请求字符串
    rubric: dict | None = None,
) -> dict
```

### rubric 参数

```python
rubric = {
    "rubric_version": "v1",
    "max_iter": 3,
    "correctness": {"threshold": 0.5},
    "safety": {"threshold": 1.0},   # 必须 = 1.0 才安全
    "idempotency": {"threshold": 0.5},
    "traceability": {"threshold": 0.5},
    "spec_compliance": {"threshold": 0.5},
}
```

### 评分维度

| 维度 | 含义 |
|------|------|
| `correctness` | exit_code=0 且有输出 |
| `safety` | destructive 操作有 pre-confirm，无凭据泄露 |
| `idempotency` | 重复执行同命令结果一致 |
| `traceability` | trace 包含完整命令+输出 |
| `spec_compliance` | 命令含 `--output json` 和 `--resource-group` |

### 返回值

```json
{
  "status": "PASS" | "SAFETY_FAIL" | "MAX_ITER",
  "scores": {
    "correctness": 1.0,
    "safety": 1.0,
    "idempotency": 1.0,
    "traceability": 1.0,
    "spec_compliance": 1.0
  },
  "iter": 1
}
```

---

## 所有支持的 Skill（31 个）

| Skill | 支持的操作 |
|-------|-----------|
| `azure-vm-ops` | vm_create, vm_start, vm_stop, vm_delete |
| `azure-aks-ops` | aks_create, aks_scale, aks_delete |
| `azure-blobstorage-ops` | container_create, blob_upload, blob_delete |
| `azure-appgateway-ops` | appgateway_create, appgateway_delete |
| `azure-loadbalancer-ops` | lb_create, lb_delete |
| `azure-frontdoor-ops` | frontdoor_create, endpoint_create, frontdoor_delete |
| `azure-vnet-ops` | vnet_create, subnet_create, vnet_delete |
| `azure-dns-ops` | dns_zone_create, dns_record_set_create, dns_zone_delete |
| `azure-nsg-ops` | nsg_create, nsg_rule_create, nsg_delete |
| `azure-keyvault-ops` | vault_create, secret_set, vault_delete |
| `azure-postgres-ops` | postgres_create, postgres_delete |
| `azure-redis-ops` | redis_create, redis_delete |
| `azure-monitor-ops` | alert_rule_create, action_group_create |
| `azure-cosmos-ops` | cosmosdb_create, sql_database_create |
| `azure-acr-ops` | acr_create, acr_delete |
| `azure-function-ops` | functionapp_create, functionapp_delete |
| `azure-sqldb-ops` | server_create, db_create |
| `azure-eventhub-ops` | namespace_create, namespace_delete |
| `azure-eventgrid-ops` | topic_create, topic_delete |
| `azure-servicebus-ops` | namespace_create, namespace_delete |
| `azure-aci-ops` | container_create, container_delete |
| `azure-appservice-ops` | webapp_create, webapp_delete |
| `azure-privateendpoint-ops` | pe_create, pe_delete |
| `azure-trafficmanager-ops` | profile_create, endpoint_update, profile_delete |
| `azure-backup-ops` | backup_vault_create, protection_enable |
| `azure-site-recovery-ops` | vault_create, vault_delete |
| `azure-apim-ops` | apim_create, apim_delete |
| `azure-file-storage-ops` | fileshare_create, fileshare_delete |
| `azure-queue-storage-ops` | queue_create, queue_delete |
| `azure-audit-ops` | activity_log_query（只读）|
| `azure-cost-ops` | cost_query（只读）|

---

## Trace 与诊断

### Trace 文件

所有执行记录在 `audit-results/gcl-trace-*.json`：

```json
{
  "id": "a1b2c3d4",
  "name": "feedback-loop healed",
  "metadata": {
    "skill": "azure-vm-ops",
    "operation": "vm_create",
    "status": "healed",
    "heal_attempts": 1
  }
}
```

### CADL Findings

升人工的异常模式自动写入 `.runtime/findings/`：

```
.runtime/findings/
├── 20260718-a1b2c3d4.json  ← 每次升人工生成一个
├── 20260718-e5f6g7h8.json
```

---

## 策略文件（高级）

如果你需要为新的 Azure 服务添加 L4 支持，在 `scripts/self_healing/` 下新增 JSON 文件：

```jsonc
{
  "skill": "azure-my-service-ops",
  "operations": {
    "my_operation": {
      "risky": false,
      "health_check": {
        "api": "az my-service show",
        "args_template": ["my-service", "show", "--name", "{{resource_name}}", "--resource-group", "{{resource_group}}", "--output", "json"],
        "parse_field": "provisioningState",
        "expected": "Succeeded"
      },
      "healing_rules": [
        {
          "condition_type": "field_not_equal",
          "condition_field": "provisioningState",
          "condition_value": "Succeeded",
          "heal_action": "az my-service wait",
          "heal_args_template": ["my-service", "wait", "--name", "{{resource_name}}", "--resource-group", "{{resource_group}}", "--created", "--interval", "30", "--timeout", "600"],
          "max_attempts": 4,
          "backoff_sec": 30
        }
      ]
    },
    "my_delete": {
      "risky": true,     // ← 危险操作，必须人工确认
      "healing_rules": []
    }
  }
}
```

添加后运行 `python scripts/self_healing/validate.py` 验证格式正确。
