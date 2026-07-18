# 快速入门

> 5 分钟上手 L4 自动化闭环

---

## 前置条件

1. 安装 Azure CLI（`az --version` 验证）
2. 配置环境变量（或使用 `--check` 模式跳过真实 Azure 调用）

```bash
export AZURE_SUBSCRIPTION_ID=your-subscription-id
export AZURE_TENANT_ID=your-tenant-id
export AZURE_CLIENT_ID=your-client-id
export AZURE_CLIENT_SECRET=your-client-secret
```

---

## 方式一：AI Agent 自动调用（推荐）

在 Agent 运行时，Agent 会根据 Skill 的 L4 段落自动决定是否使用闭环。

你只需要告诉 Agent 要做什么：

```
帮我创建一个 VM，名字是 my-vm，资源组是 my-rg，区域是 eastus
```

Agent 自动判断是否需要闭环，然后执行。

---

## 方式二：直接用 Python 调用

### 示例 1：创建 VM 并等待就绪

```python
import sys
sys.path.insert(0, "scripts")
from auto_feedback_loop import run_with_feedback

result = run_with_feedback(
    skill="azure-vm-ops",
    operation="vm_create",
    command=(
        "az vm create "
        "--name my-vm "
        "--resource-group my-rg "
        "--location eastus "
        "--image UbuntuLTS "
        "--size Standard_DS2_v2 "
        "--admin-username azureuser "
        "--generate-ssh-keys"
    ),
    desired_state={"statuses[1].displayStatus": "VM running"},
    risky=False,
)

print(result.status)      # success | healed | escalated | failed
print(result.message)   # 人类可读摘要
print(result.trace_id)  # 关联 trace ID
```

**会发生什么：**

1. 执行 `az vm create`
2. 调用 `az vm get-instance-view` 观察 VM 状态
3. 比对 desired_state，发现 VM running → 一致 → `status="success"`

---

### 示例 2：创建 AKS 集群

```python
from auto_feedback_loop import run_with_feedback

result = run_with_feedback(
    skill="azure-aks-ops",
    operation="aks_create",
    command=(
        "az aks create "
        "--name my-aks "
        "--resource-group my-rg "
        "--location eastus "
        "--node-count 3 "
        "--node-vm-size Standard_DS2_v2 "
        "--generate-ssh-keys"
    ),
    desired_state={"provisioningState": "Succeeded"},
    risky=False,
)
```

**如果集群创建后状态不是 Succeeded**，系统会自动：
1. 调用 `az aks wait` 等待集群就绪（最多 4 次，每次间隔 30 秒）
2. 还不行就升人工

---

### 示例 3：危险操作（delete）跳过闭环

```python
# risky=True → 永远跳过闭环，要求人工确认
result = run_with_feedback(
    skill="azure-vm-ops",
    operation="vm_delete",
    command="az vm delete --name my-vm --resource-group my-rg --yes",
    desired_state={},
    risky=True,   # ← 必须人工确认
)
print(result.status)  # escalated（要求确认）
print(result.escalation)  # 含人工确认提示
```

---

## 方式三：命令行工具

```bash
# 完整闭环（dry-run 验证流程）
python scripts/auto_feedback_loop.py \
  --skill azure-vm-ops \
  --operation vm_create \
  --command "az vm create --name my-vm --resource-group my-rg --location eastus --image UbuntuLTS" \
  --desired-state '{"statuses[1].displayStatus": "VM running"}'

# 只验证，不执行
python scripts/auto_feedback_loop.py \
  --skill azure-vm-ops \
  --operation vm_create \
  --command "az vm create ..." \
  --desired-state '{}' \
  --dry-run
```

---

## 方式四：使用 GCL 质量门（无 desired_state）

如果你只想验证一个命令是否安全（不关心修复），用 `gcl_runner.py`：

```bash
python scripts/gcl_runner.py azure-vm-ops '{}' \
  "az vm show --name my-vm --resource-group my-rg --output json"
```

输出示例：

```json
{
  "status": "PASS",
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

## 下一步

- 完整参数说明 → [用户指南](user-guide.md)
- 常见问题 → [FAQ](faq.md)
- 执行路径决策树 → [了解何时用哪个工具](user-guide.md#决策树)
