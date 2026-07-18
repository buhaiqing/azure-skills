# 常见问题（FAQ）

---

## 基础问题

### Q1: 状态是什么含义？

| status | 发生了什么 | 你该做什么 |
|--------|-----------|-----------|
| `success` | 命令成功 + 资源状态匹配 desired_state | 无 |
| `healed` | 命令成功但初始状态不对 → 自动修复成功 | 确认修复结果是否符合预期 |
| `escalated` | 命令成功但状态不对，且修复不了 | 看 `escalation` 消息，按建议处理 |
| `failed` | 命令本身失败（如参数错误） | 修命令后重试 |

---

### Q2: 升人工了怎么办？

看 `result.escalation` 字段，包含：

- 执行了什么命令
- 错误是什么
- 补偿历史（如果尝试了修复）
- Trace ID
- 4 条建议操作步骤

```
⚠️  需要人工介入 — azure-vm-ops / vm_create

命令: `az vm start ...`
退出码: `1`
错误: VM is already started

补偿历史:
  ✅ Attempt 1: az vm start → exit=1
  ❌ Attempt 2: az vm start → exit=1

Trace ID: `a1b2c3d4`

**建议操作:**
1. 登录 Azure Portal 检查资源当前状态
2. 查看 Activity Log
3. 确认配额
4. 修复后附 Trace ID 重新提交
```

---

### Q3: `risky=True` 是什么？

危险操作（delete、stop、deallocate、purge、scale-to-zero）**永远不走自动闭环**，必须人工输入 exact 资源名称确认。

```python
# 删除 VM — 必须人工确认
run_with_feedback(
    skill="azure-vm-ops",
    operation="vm_delete",
    command="az vm delete --name my-vm --resource-group my-rg --yes",
    desired_state={},
    risky=True,  # ← 这行强制跳过闭环
)
# 返回 status="escalated"，escalation 消息要求确认
```

---

### Q4: 我不想用闭环，怎么关闭？

```python
# 方法 1：不传 desired_state（不推荐，闭环的好处全丢了）
run_with_feedback(skill="azure-vm-ops", operation="vm_delete",
                 command="az vm start --name my-vm ...", desired_state={})

# 方法 2：用 --dry-run 测试
python scripts/auto_feedback_loop.py --dry-run --skill azure-vm-ops ...

# 方法 3：用 gcl_runner.py 做质量门（无自动修复）
python scripts/gcl_runner.py azure-vm-ops '{}' "az vm show ..."
```

---

## 技术问题

### Q5: 没有 Azure 凭据，怎么测试？

```python
# 全部走 dry-run，不实际执行 az 命令
result = run_with_feedback(
    skill="azure-vm-ops",
    operation="vm_create",
    command="az vm create ...",
    desired_state={},
    dry_run=True,  # ← 不执行，只验证流程
)
# status = "escalated"（dry-run 跳过执行，自然升人工）
```

---

### Q6: `desired_state` 字段怎么知道填什么？

参考策略文件 `scripts/self_healing/` 里的 `expected` 字段：

```bash
# 查看 vm_heal.json
cat scripts/self_healing/vm_heal.json
# 找 health_check.expected
```

常用字段参考表：

| 资源类型 | 观察字段 | 期望值 |
|---------|---------|--------|
| VM | `statuses[1].displayStatus` | `VM running` |
| AKS | `provisioningState` | `Succeeded` |
| Key Vault | `properties.provisioningState` | `Succeeded` |
| Blob Container | `name` | `container名` |
| App Service | `state` | `Running` |
| SQL DB | `status` | `Online` |
| Cosmos DB | `provisioningState` | `Succeeded` |

---

### Q7: 修复次数用完了还是失败怎么办？

系统升人工。你会收到：
1. 完整错误上下文
2. 已尝试的修复历史
3. Trace ID

你可以：
1. 登录 Azure Portal 手动检查资源状态
2. 根据错误原因修复问题
3. 重新提交任务（附 Trace ID 方便关联）

---

### Q8: 我怎么知道升人工的原因？

查看 trace 文件（根据 `trace_id` 查找）：

```bash
ls audit-results/gcl-trace-*.json | xargs grep "a1b2c3d4"
```

或查看 findings：

```bash
ls .runtime/findings/*.json
cat .runtime/findings/20260718-a1b2c3d4.json
```

---

### Q9: 可以自定义修复策略吗？

可以。在 `scripts/self_healing/` 下新建或编辑 JSON 文件。

例如：VM 非 running 时，不只是 start，还想发通知：

```jsonc
{
  "skill": "azure-vm-ops",
  "operations": {
    "vm_create": {
      "risky": false,
      "health_check": { ... },
      "healing_rules": [
        {
          "condition_type": "field_not_equal",
          "condition_field": "statuses[1].displayStatus",
          "condition_value": "VM running",
          "heal_action": "az vm start",
          "heal_args_template": ["vm", "start", "--name", "{{vm_name}}", "--resource-group", "{{resource_group}}"],
          "max_attempts": 2,
          "backoff_sec": 30
        }
      ]
    }
  }
}
```

添加后验证：`python scripts/self_healing/validate.py`

---

### Q10: 想看现在的修复策略有哪些？

```bash
# 列出所有 skill 的策略
ls scripts/self_healing/*_heal.json | sed 's/.*\///; s/_heal.json//'

# 看某个 skill 的具体策略
cat scripts/self_healing/vm_heal.json
```

---

### Q11: 凭据会不会泄露到 trace 里？

不会。`az_trace.py` 有凭据检测逻辑，会自动 mask：

```
AZURE_CLIENT_SECRET → ***
```

发现凭据泄露时，`safety=0`，操作立即 ABORT。
