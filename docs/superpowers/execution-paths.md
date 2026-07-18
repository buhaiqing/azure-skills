# Azure Skills 执行路径决策树

> Agent 执行 Azure 云操作时，如何选择正确的执行框架

---

## 执行路径总览

```
Agent 收到 Azure 操作请求
        │
        ▼
┌──────────────────────────────────────┐
│  Step 1: 问自己三个问题              │
│                                      │
│  Q1. 操作有 desired_state 吗？        │  ← 用户或 Skill 定义了期望状态
│      (例如：VM 运行中、集群已创建)      │
│                                      │
│  Q2. 需自动修复（self-heal）吗？      │  ← 操作失败后自动补偿，不需要人工介入
│      (非 destructive 操作)            │
│                                      │
│  Q3. 是 destructive / risky 操作吗？ │  ← delete / stop / purge / scale-to-zero
│      (delete, stop, deallocate 等)   │
└──────────────────────────────────────┘
        │
        ▼
```

---

## 决策矩阵

| 场景 | 框架 | 说明 |
|------|------|------|
| 有 desired_state + 非 risky + 需修复 | **`auto_feedback_loop.py`** | 完整 L4 闭环：execute→observe→diff→heal/escalate |
| risky 操作（delete/stop）| **SKILL.md Safety Gate** | 永远 bypass 自动闭环，必须 human confirmation |
| 无 desired_state + 需质量门 | **`gcl_runner.py`** | GCL Generator+Critic，量化评分（correctness/safety/idempotency/traceability/spec_compliance）|
| 两者都要 | **先 gcl_runner → 再 auto_feedback_loop** | GCL 安全门先行，修复闭环在后 |

---

## 详细路径

### 路径 A：`auto_feedback_loop.py`（L4 自动修复）

**触发条件**：操作有 `desired_state` 且非 risky

**典型场景**：
- 创建 VM → 等待 `VM running` → 若非 running 自动 `az vm start`
- 创建 AKS 集群 → 等待 `provisioningState=Succeeded` → 若未就绪自动 `az aks wait`
- 创建 blob 容器 → 等待容器存在 → 若不存在自动重试

**使用方式**：
```bash
python scripts/auto_feedback_loop.py \
  --skill azure-vm-ops \
  --operation vm_create \
  --command "az vm create --name {{user.vm_name}} --resource-group {{user.resource_group}} ..." \
  --desired-state '{"statuses[1].displayStatus": "VM running"}' \
  [--dry-run] [--trace-id <uuid>]
```

**返回值**：`FeedbackResult(status: success|healed|escalated|failed, heal_attempts, trace_id)`

**CADL**：escalation 时自动写 `.runtime/findings/<date>-<id8>.json`

---

### 路径 B：Safety Gate（Human Confirmation）

**触发条件**：`risky=True`（delete / stop / deallocate / purge / scale-to-zero）

**行为**：永远 bypass `auto_feedback_loop.py`，必须显式 human confirmation

**典型场景**：
- `az vm delete` → 必须用户输入 exact VM name
- `az aks delete` → 必须用户确认 cluster name
- `az storage account delete` → 必须用户确认 account name

**在 SKILL.md 中标注**：
```
## L4 Auto-Feedback Loop
- **Risky operations** (delete, stop): always bypass loop and require explicit human confirmation
```

---

### 路径 C：`gcl_runner.py`（GCL 质量门）

**触发条件**：需量化评分（correctness/safety/idempotency/traceability/spec_compliance）

**典型场景**：
- destructive 操作前的安全检查（先 `az vm show` 确认，再执行 delete）
- 关键操作的 idempotency 验证
- trace 完整性检查

**使用方式**：
```bash
python scripts/gcl_runner.py azure-vm-ops '{"rubric_version":"v1"}' \
  "az vm show --name my-vm --resource-group my-rg --output json"
```

**返回值**：`{"status": PASS|SAFETY_FAIL|MAX_ITER, "scores": {...}, "iter": N}`

**CADL**：`SAFETY_FAIL` / `MAX_ITER` 时自动写 `.runtime/findings/`

---

### 路径 D：组合路径（GCL → L4）

**触发条件**：高风险操作 + 修复 + 需质量门

**执行顺序**：
1. `gcl_runner.py` → 确保 safety=1（先验证再执行）
2. `auto_feedback_loop.py` → 自动修复（create 后等待就绪）

**示例**：创建 VM 并确保运行
```bash
# Step 1: GCL 验证
python scripts/gcl_runner.py azure-vm-ops '{}' "az vm create ..."

# Step 2: L4 修复
python scripts/auto_feedback_loop.py --skill azure-vm-ops --operation vm_create ...
```

---

## 快速决策卡片

```
你是 Agent，执行 Azure 操作：

  是否 destructive（delete/stop/purge/scale-zero）？
    → YES  → Human Confirmation Gate（跳过所有自动闭环）
    → NO   → 继续

  有 desired_state 吗？
    → YES  → auto_feedback_loop.py（L4 闭环）
    → NO   → 继续

  需量化质量门吗？
    → YES  → gcl_runner.py（GCL）
    → NO   → 直接执行 az 命令
```

---

## 文件对应关系

| 文件 | 职责 | trace 位置 |
|------|------|-----------|
| `scripts/auto_feedback_loop.py` | L4 闭环（execute→observe→diff→heal） | `audit-results/gcl-trace-*.json` |
| `scripts/gcl_runner.py` | GCL 评分（Generator+Critic） | `audit-results/gcl-trace-*.json` |
| `scripts/report_finding.py` | CADL findings 写入 | `.runtime/findings/` |
| `scripts/self_healing/*.json` | 31 个 skill 的修复策略 | — |
| `scripts/az_trace.py` | az 命令 auto-trace | `audit-results/` |

---

## 相关文档

- [Spec: Gartner L4 Auto-Feedback Loop](specs/2026-07-18-gartner-l4-auto-feedback-loop.md)
- [Plan: L4 Strategy Expansion](plans/2026-07-18-l4-strategy-expansion.md)
- `AGENTS.md §GCL` — GCL rubric 和 trace schema
- `AGENTS.md §CADL` — 复利资产沉淀机制
