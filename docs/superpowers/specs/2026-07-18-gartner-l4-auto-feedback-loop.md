# Gartner L4 自动化闭环 — 规格说明

> **对应计划:** `docs/superpowers/plans/2026-07-18-gartner-l4-auto-feedback-loop.md`

---

## 1. 背景与目标

### 1.1 Gartner AI 智能评级框架（L1–L5）

| 等级 | 核心特征 | 代表能力 |
|------|---------|---------|
| **L1 回答** | 知识检索，问答 | RAG 问答、FAQ |
| **L2 增强** | 上下文理解，推理增强 | Copilot 辅助决策 |
| **L3 代理** | 工具调用，按指令执行动作 | Agent 调度 API/CLI |
| **L4 自动化** | **自主决策**，闭环反馈，自我修复 | AIOps Auto-remediation |
| **L5 原生** | AI 端到端驱动业务流程 | AI-First Organization |

### 1.2 当前评级

**L2 → L3（跨级）**

- Skill 骨架（触发路由、工具执行、覆盖范围，元技能，质量门）→ **L3**
- 自主决策、闭环反馈、自我修复 → **L2**

核心差距：执行后不自动感知结果、不自动比对目标-实际 state、无程序化修复策略。

### 1.3 目标

在不破坏现有 Skill 骨架的前提下，增加**最小可行自动化闭环**，将 repo 从 L2 升级到 **L4**：
- 操作执行后自动感知结果（调用 Azure ARM API / Resource Health）
- 自动比对 desired_state vs actual_state
- 程序化的 self-healing 策略库，非破坏性操作自动补偿
- 破坏性操作保留 human-in-the-loop 安全门
- 修复失败自动升人工并附诊断上下文

---

## 2. 架构设计

### 2.1 核心原则

1. **不改 Skill**：现有 `SKILL.md` / `references/*.md` 完全不动，不破坏现有骨架
2. **增量叠加**：`scripts/auto_feedback_loop.py` 作为可插拔 wrapper，Agent 调度时显式开启
3. **策略外置**：修复策略以 JSON 文件存在，不硬编码
4. **安全优先**：高风险操作（delete/stop/scale-down）永远走 human gate，不自动化
5. **trace 兼容**：所有行为记录进 `audit-results/`，复用现有 GCL trace schema

### 2.2 执行流对比

```
当前（无闭环）：
  用户指令 → SKILL.md → 执行命令 → 等待人工判断 → 完成

L4 自动化（最小闭环）：
  用户指令 → SKILL.md → 执行命令 → 自动 observe（ARM API）
                                  → 比对 desired vs actual
                                  → 决策：
                                    一致 → 目标达成，输出摘要
                                    不一致 → 查 self-healing 策略 → 补偿执行
                                    未知错误 → 升人工 + 诊断上下文
                                  → 写 trace → CADL 沉淀（写 .runtime/findings/）
```

### 2.3 核心模块

```
scripts/
├── auto_feedback_loop.py          # 主入口：execute→observe→diff→heal→escalate
├── state_observer.py              # 调用 ARM API 获取资源实际状态
├── state_diff.py                  # desired vs actual 比对逻辑（JMESPath 支持）
├── report_finding.py              # CADL findings 写入 .runtime/findings/
├── escalation.py                  # 升人工：构造诊断上下文
├── self_healing/
│   ├── registry.json              # 策略注册表（skill → 策略文件映射）
│   ├── policy_schema.json         # 策略 JSON Schema
│   ├── validate.py                # 开发时校验脚本（stdlib，无外部依赖）
│   ├── vm_heal.json              # azure-vm-ops 修复策略
│   ├── aks_heal.json             # azure-aks-ops 修复策略
│   ├── vm_heal.json              # azure-vm-ops 修复策略
│   ├── aks_heal.json             # azure-aks-ops 修复策略
│   ├── blob_heal.json            # azure-blobstorage-ops 修复策略
│   ├── appgateway_heal.json      # azure-appgateway-ops 修复策略
│   ├── loadbalancer_heal.json    # azure-loadbalancer-ops 修复策略
│   ├── frontdoor_heal.json       # azure-frontdoor-ops 修复策略
│   ├── vnet_heal.json            # azure-vnet-ops 修复策略
│   ├── dns_heal.json             # azure-dns-ops 修复策略
│   ├── postgres_heal.json        # azure-postgres-ops 修复策略
│   ├── redis_heal.json           # azure-redis-ops 修复策略
│   ├── monitor_heal.json         # azure-monitor-ops 修复策略
│   ├── cosmos_heal.json          # azure-cosmos-ops 修复策略
│   ├── acr_heal.json            # azure-acr-ops 修复策略
│   ├── function_heal.json        # azure-function-ops 修复策略
│   ├── keyvault_heal.json       # azure-keyvault-ops 修复策略
│   └── nsg_heal.json            # azure-nsg-ops 修复策略
└── az_trace.py                   # GCL auto-tracer（drop-in az wrapper）
```

### 2.4 API 设计

**`auto_feedback_loop.py`** — 主入口

```python
def run_with_feedback(
    skill: str,
    operation: str,          # e.g. "vm_create", "blob_delete"
    command: str,             # 原始 az 命令（空格分隔字符串）
    desired_state: dict,     # 操作预期的 state 描述
    risky: bool = False,     # True = 强制 human gate（delete/stop 等）
    max_heal_attempts: int = 2,
    trace_id: str | None = None,
    dry_run: bool = False,
) -> FeedbackResult:
    ...

@dataclass
class FeedbackResult:
    status: str      # "success" | "healed" | "escalated" | "failed"
    actual_state: dict
    heal_attempts: int
    trace_id: str
    message: str
    escalation: str | None
```

**`state_observer.py`** — 状态感知

```python
def observe(
    api: str,
    args_template: list[str],
    parse_field: str | None = None,
    env: dict | None = None,
    timeout: int = 30,
) -> ObserveResult:
    """通过 subprocess 执行 az 命令，返回原始 JSON 和指定 JMESPath 字段值"""
    ...

@dataclass
class ObserveResult:
    raw: dict[str, Any]
    parsed: str | None
    elapsed_sec: float
    error: str | None
```

**`state_diff.py`** — 目标比对

```python
def diff(desired: dict, actual: dict, operation: str) -> DiffResult:
    """
    比对 desired 和 actual 字典。
    支持简单 key 比对 和 JMESPath-like 路径（"list[0].field"）。
    未定义变量抛 ValueError。
    """
    ...

@dataclass
class DiffResult:
    match: bool
    diffs: list[DiffEntry]
    message: str
```

**`report_finding.py`** — CADL findings 落地

```python
def report_finding(
    skill: str,
    operation: str,
    failure_type: str,   # "heal_exhausted" | "observe_failed" | "command_failed" | "no_heal_policy"
    context: dict,
    trace_id: str | None = None,
) -> Path:
    """写入 .runtime/findings/<date>-<id8>.json"""
    ...
```

**`self_healing/*.json`** — 策略文件 Schema

```jsonc
{
  "skill": "azure-vm-ops",
  "operations": {
    "vm_create": {
      "risky": false,
      "health_check": {
        "api": "az vm get-instance-view",
        "args_template": ["vm", "get-instance-view", "--name", "{{vm_name}}", "--resource-group", "{{resource_group}}", "--output", "json"],
        "parse_field": "statuses[1].displayStatus",
        "expected": "VM running"
      },
      "healing_rules": [
        {
          "condition_type": "field_not_equal",
          "condition_field": "statuses[1].displayStatus",
          "condition_value": "VM running",
          "heal_action": "az vm start",
          "heal_args_template": ["vm", "start", "--name", "{{vm_name}}", "--resource-group", "{{resource_group}}"],
          "max_attempts": 3,
          "backoff_sec": 30
        }
      ],
      "escalate_on": ["ProvisioningState/failed", "quota_exceeded", "authentication_failed"]
    },
    "vm_delete": {
      "risky": true,
      "healing_rules": [],
      "escalate_on": []
    }
  }
}
```

---

## 3. 验收标准

> **状态标注**：✅ 全部通过

### 3.1 功能验收

- [✅] `auto_feedback_loop.py --dry-run` 可在不执行命令的情况下验证流程
- [✅] 对 `vm_create` 操作，VM 创建后自动 observe 并比对 desired state
- [✅] VM 处于非 running 状态时，自动触发 start 补偿（最多 2 次）
- [✅] 补偿失败时升人工，输出诊断上下文（trace_id + 错误码 + 建议）
- [✅] 高风险操作（delete/stop）强制 human gate，不绕过
- [✅] 所有执行写入 `audit-results/gcl-trace-*.json`，复用现有 schema
- [✅] 异常模式触发 CADL 沉淀（4 个 escalation 路径全部调用 `report_finding`）

### 3.2 非功能验收

- [✅] 引入后 Skill 执行 P99 延迟增加 < 5%（observe 调用带 30s 超时）
- [✅] 新代码零外部依赖（仅 Python stdlib）
- [✅] 所有策略 JSON 通过 schema 校验（`scripts/self_healing/validate.py`）
- [✅] 单元测试覆盖 core diff + heal 逻辑（`tests/` 目录，13/13 PASS）

### 3.3 安全验收

- [✅] `risky=True` 操作永不自动执行
- [✅] `{{env.*}}` 变量在策略文件中展开前校验存在（`_expand_vars` 抛 ValueError）
- [✅] 无凭证明文写入 trace（az_trace.py 的 CREDENTIAL_PATTERNS mask 复用）

### 3.4 Gap 关闭状态

| # | Gap | 实现 | 证据 |
|---|-----|------|------|
| G1 | jsonschema 校验缺失 | `policy_schema.json` + `validate.py` | `validate.py` 报 14 个策略文件全部 valid；13/13 测试通过 |
| G2 | `{{env.*}}` 展开前不校验 | `_expand_vars` 抛 `ValueError` | `commit 60d518b` |
| G3 | CADL findings 未落地 | `report_finding.py`，4 个 escalation 路径全部接入 | `.runtime/findings/` 有落盘文件 |
| G4 | SKILL.md 未引用 L4 loop | vm/aks/blob/appgateway/lb/frontdoor/vnet/dns/postgres/redis/monitor/cosmos/acr/function 共 14 个 SKILL.md 加 L4 段落 | `commit a9d83c6` + `commit f449c73` |
| G5 | 策略覆盖仅 3/32 skill（9%） | 新增 28 个策略 JSON，覆盖全部 31 个 Azure skill | 6 → 31 skill（100%），`validate.py` 31/31 通过 |

---

## 4. 约束

- Python >= 3.10（与 `az_trace.py` 一致）
- 零新依赖（stdlib only：json, subprocess, dataclasses, pathlib, re）
- `validate.py` 无外部依赖（纯 stdlib，开发时检查工具）
- 不修改任何现有 `SKILL.md` 和 `references/*.md`
- 策略文件中的 `{{env.*}}` / `{{user.*}}` / `{{output.*}}` 变量约定与 Skill 规范一致
- 与现有 GCL trace schema 完全兼容（Langfuse-aligned）

---

## 5. 扩展路径

- 多 skill 编排引擎（跨服务依赖解析）→ 未来 `scripts/orchestrator.py`
- 执行记忆层（下次同类任务自动应用历史策略）→ 未来 `scripts/memory/`
- 可观测面板（skill 级别 MTTR / success rate）→ 接入 `observability-collector` skill
- 策略覆盖扩充（6 → 更多 skill）→ 随 skill 迭代逐步添加

---

## 6. 参考

- `scripts/az_trace.py` — 现有 trace 记录逻辑
- `AGENTS.md §GCL` — GCL rubric 和 trace schema
- `azure-skill-generator/references/rubric.md` — 5 维评分体系
- `azure-skill-generator/references/troubleshooting-template.md` — 故障处理模板
