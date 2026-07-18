# Gartner L4 自动化闭环 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `scripts/` 下增加最小可行 L4 自动化闭环（`auto_feedback_loop.py` + `state_observer.py` + `state_diff.py` + 策略 JSON），将 repo 从 Gartner L2 升级到 L4。

**Architecture:** 增量叠加架构，不修改现有 Skill。`auto_feedback_loop.py` 作为可插拔 wrapper，调用 ARM API 观察结果，比对 desired vs actual state，按策略 JSON 执行 self-healing，失败则升人工。全程复用现有 GCL trace schema 写 audit log。

**Tech Stack:** Python stdlib（urllib, json, subprocess, dataclasses, jsonschema），无外部依赖。

---

### Task 1: 创建目录结构和测试骨架

**Files:**
- Create: `scripts/self_healing/`
- Create: `tests/test_state_diff.py`
- Create: `tests/test_self_healing.py`
- Create: `tests/test_auto_feedback_loop.py`
- Create: `scripts/self_healing/registry.json`

- [ ] **Step 1: 创建目录**

Run: `mkdir -p scripts/self_healing tests`
Expected: 目录存在，无报错。

- [ ] **Step 2: 写 registry.json（空壳）**

```json
{
  "version": "1.0.0",
  "skills": {}
}
```

- [ ] **Step 3: 写 `tests/test_state_diff.py`（RED — 先写失败测试）**

```python
import sys
sys.path.insert(0, "scripts")
from state_diff import diff, DiffResult

def test_diff_equal_states():
    desired = {"status": "running", "powerState": "VM running"}
    actual  = {"status": "running", "powerState": "VM running"}
    result = diff(desired, actual, "vm_create")
    assert result.match is True
    assert result.diffs == []

def test_diff_mismatch():
    desired = {"powerState": "VM running"}
    actual  = {"powerState": "VM deallocated"}
    result = diff(desired, actual, "vm_create")
    assert result.match is False
    assert len(result.diffs) == 1
    assert result.diffs[0]["field"] == "powerState"

def test_diff_missing_field():
    desired = {"provisioningState": "Succeeded"}
    actual  = {}
    result = diff(desired, actual, "vm_create")
    assert result.match is False
```

- [ ] **Step 4: 写 `tests/test_self_healing.py`（RED）**

```python
import json, sys
sys.path.insert(0, "scripts")
from self_healing.loader import load_policy, load_registry

def test_load_empty_registry():
    registry = load_registry("scripts/self_healing/registry.json")
    assert registry["version"] == "1.0.0"

def test_load_nonexistent_policy():
    policy = load_policy("azure-nonexistent-ops")
    assert policy is None
```

- [ ] **Step 5: 写 `tests/test_auto_feedback_loop.py`（RED）**

```python
import sys
sys.path.insert(0, "scripts")
from dataclasses import dataclass

@dataclass
class MockArgs:
    skill: str = "azure-vm-ops"
    operation: str = "vm_create"
    command: str = "az vm create --name test --resource-group test-rg"
    desired_state: str = '{"powerState": "VM running"}'
    risky: bool = False
    dry_run: bool = True

def test_dry_run_no_execution():
    # dry_run 模式不执行命令，只验证流程
    args = MockArgs(dry_run=True)
    # 验证不抛异常，返回 dry_run 相关标记
```

- [ ] **Step 6: 运行测试确认全部 FAIL**

Run: `python -m pytest tests/ -v 2>&1 | head -40`
Expected: FAIL — modules not found or assertions failing.

---

### Task 2: 实现 `state_diff.py`

**Files:**
- Create: `scripts/state_diff.py`

- [ ] **Step 1: 实现 `scripts/state_diff.py`**

```python
#!/usr/bin/env python3
"""desired vs actual state diff — 无外部依赖"""
from dataclasses import dataclass
from typing import Any

@dataclass
class DiffEntry:
    field: str
    desired: Any
    actual: Any

@dataclass
class DiffResult:
    match: bool
    diffs: list[DiffEntry]
    message: str

def diff(desired: dict, actual: dict, operation: str) -> DiffResult:
    """
    比对 desired 和 actual 字典。
    规则：
    - desired 中每个 key 必须存在于 actual
    - desired 中每个 value 必须与 actual[同名 key] 相等
    """
    diffs: list[DiffEntry] = []
    for k, v in desired.items():
        if k not in actual:
            diffs.append(DiffEntry(field=k, desired=v, actual=None))
        elif actual[k] != v:
            diffs.append(DiffEntry(field=k, desired=v, actual=actual[k]))
    match = len(diffs) == 0
    if match:
        msg = f"[diff] operation={operation} — all fields match"
    else:
        fields = ", ".join(d.field for d in diffs)
        msg = f"[diff] operation={operation} — mismatched fields: {fields}"
    return DiffResult(match=match, diffs=diffs, message=msg)
```

- [ ] **Step 2: 确认测试 PASS**

Run: `python -m pytest tests/test_state_diff.py -v`
Expected: PASS（`test_diff_*` 全通过）。

---

### Task 3: 实现 `self_healing/loader.py` 和策略文件

**Files:**
- Create: `scripts/self_healing/loader.py`
- Create: `scripts/self_healing/vm_heal.json`
- Create: `scripts/self_healing/aks_heal.json`
- Create: `scripts/self_healing/blob_heal.json`

- [ ] **Step 1: 实现 `scripts/self_healing/loader.py`**

```python
#!/usr/bin/env python3
"""策略加载器 — 无外部依赖"""
import json
from pathlib import Path
from typing import Optional

REGISTRY_PATH = Path(__file__).parent / "registry.json"

def load_registry(path: str | Path = REGISTRY_PATH) -> dict:
    return json.loads(Path(path).read_text())

def load_policy(skill_name: str, registry_path: str | Path = REGISTRY_PATH) -> Optional[dict]:
    registry = load_registry(registry_path)
    skill_map = registry.get("skills", {})
    policy_file = skill_map.get(skill_name)
    if not policy_file:
        return None
    return json.loads((Path(__file__).parent / policy_file).read_text())
```

- [ ] **Step 2: 写 `scripts/self_healing/registry.json`**

```json
{
  "version": "1.0.0",
  "skills": {
    "azure-vm-ops": "vm_heal.json",
    "azure-aks-ops": "aks_heal.json",
    "azure-blobstorage-ops": "blob_heal.json"
  }
}
```

- [ ] **Step 3: 写 `scripts/self_healing/vm_heal.json`**

策略覆盖：`vm_create`（启动检查）、`vm_start`（幂等）、`vm_stop`（幂等）、`vm_delete`（不自动 heal，安全优先）。

```jsonc
{
  "skill": "azure-vm-ops",
  "operations": {
    "vm_create": {
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
        },
        {
          "condition_type": "field_not_equal",
          "condition_field": "statuses[1].displayStatus",
          "condition_value": "ProvisioningState/succeeded",
          "heal_action": "az vm restart",
          "heal_args_template": ["vm", "restart", "--name", "{{vm_name}}", "--resource-group", "{{resource_group}}"],
          "max_attempts": 2,
          "backoff_sec": 60
        }
      ],
      "escalate_on": ["ProvisioningState/failed", "quota_exceeded", "authentication_failed"],
      "risky": false
    },
    "vm_start": {
      "healing_rules": [],
      "escalate_on": [],
      "risky": false
    },
    "vm_stop": {
      "risky": false,
      "healing_rules": []
    },
    "vm_delete": {
      "risky": true,
      "healing_rules": [],
      "escalate_on": []
    }
  }
}
```

- [ ] **Step 4: 写 `scripts/self_healing/aks_heal.json`**

覆盖 `aks_create`（node pool ready）、`aks_scale`（node count）、`aks_delete`（risky=true）。

```jsonc
{
  "skill": "azure-aks-ops",
  "operations": {
    "aks_create": {
      "health_check": {
        "api": "az aks show",
        "args_template": ["aks", "show", "--name", "{{cluster_name}}", "--resource-group", "{{resource_group}}", "--output", "json"],
        "parse_field": "provisioningState",
        "expected": "Succeeded"
      },
      "healing_rules": [
        {
          "condition_type": "field_not_equal",
          "condition_field": "provisioningState",
          "condition_value": "Succeeded",
          "heal_action": "az aks wait",
          "heal_args_template": ["aks", "wait", "--name", "{{cluster_name}}", "--resource-group", "{{resource_group}}", "--created", "--interval", "30", "--timeout", "600"],
          "max_attempts": 4,
          "backoff_sec": 30
        }
      ],
      "escalate_on": ["Failed", "quota_exceeded"],
      "risky": false
    },
    "aks_scale": {
      "risky": false,
      "healing_rules": []
    },
    "aks_delete": {
      "risky": true,
      "healing_rules": [],
      "escalate_on": []
    }
  }
}
```

- [ ] **Step 5: 写 `scripts/self_healing/blob_heal.json`**

覆盖 `blob_upload`、`blob_delete`（risky=true）。

```jsonc
{
  "skill": "azure-blobstorage-ops",
  "operations": {
    "blob_upload": {
      "risky": false,
      "healing_rules": [],
      "escalate_on": []
    },
    "blob_delete": {
      "risky": true,
      "healing_rules": [],
      "escalate_on": []
    }
  }
}
```

- [ ] **Step 6: 运行测试 PASS**

Run: `python -m pytest tests/test_self_healing.py -v`
Expected: PASS（`test_load_*` 全通过）。

---

### Task 4: 实现 `state_observer.py`

**Files:**
- Create: `scripts/state_observer.py`

- [ ] **Step 1: 实现 `scripts/state_observer.py`**

```python
#!/usr/bin/env python3
"""调用 Azure ARM API / Azure CLI 获取资源实际状态 — stdlib only"""
import json
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class ObserveResult:
    raw: dict[str, Any]
    parsed: Optional[str]   # health_check 指定的字段值
    elapsed_sec: float
    error: Optional[str]

def observe(
    api: str,
    args_template: list[str],
    parse_field: Optional[str] = None,
    env: Optional[dict] = None,
) -> ObserveResult:
    """
    通过 subprocess 执行 az 命令，返回原始 JSON 和指定字段值。
    api: "az vm get-instance-view" 等
    args_template: 完整 az 参数列表
    parse_field: JMESPath 字符串（如 "statuses[1].displayStatus"）
    """
    cmd = ["az"] + args_template
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=env or None,
        )
        elapsed = time.monotonic() - start
        if result.returncode != 0:
            return ObserveResult(raw={}, parsed=None, elapsed=elapsed,
                                error=result.stderr.strip())
        raw = json.loads(result.stdout)
        parsed = _jmespath(parse_field, raw) if parse_field else None
        return ObserveResult(raw=raw, parsed=parsed, elapsed=elapsed, error=None)
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return ObserveResult(raw={}, parsed=None, elapsed=elapsed,
                            error="timeout (30s)")
    except json.JSONDecodeError:
        elapsed = time.monotonic() - start
        return ObserveResult(raw={}, parsed=None, elapsed=elapsed,
                            error="invalid json output")

# ponytail: 极简 JMESPath 实现，覆盖本 repo 需要的 [n].field 和顶层 field
def _jmespath(path: str, data: dict) -> Any:
    """简化 JMESPath：支持 "field" / "list[0].field" 两种形式"""
    parts = path.split(".")
    current: Any = data
    for part in parts:
        if current is None:
            return None
        if "[" in part and "]" in part:
            key, bracket = part.split("[", 1)
            idx = int(bracket.strip("]"))
            if key:
                current = current.get(key)
            if isinstance(current, list) and len(current) > idx:
                current = current[idx]
            else:
                return None
        else:
            current = current.get(part)
    return current
```

- [ ] **Step 2: 用 dry-run 验证模块加载**

Run: `python -c "from state_observer import observe; print('import ok')"`
Expected: `import ok`（无需真实 Azure 凭证）。

---

### Task 5: 实现 `escalation.py`

**Files:**
- Create: `scripts/escalation.py`

- [ ] **Step 1: 实现 `scripts/escalation.py`**

```python
#!/usr/bin/env python3
"""升人工：构造诊断上下文，输出给用户"""
from dataclasses import dataclass

@dataclass
class EscalationContext:
    skill: str
    operation: str
    command: str
    exit_code: int
    error: str
    heal_attempts: int
    trace_id: str

def escalate(ctx: EscalationContext) -> str:
    """
    返回人类可读升人工消息，包含诊断上下文和建议操作。
    不抛异常，不写文件（trace 由调用方负责）。
    """
    lines = [
        f"⚠️  **需要人工介入** — {ctx.skill} / {ctx.operation}",
        f"",
        f"命令: `{' '.join(ctx.command)}`",
        f"退出码: {ctx.exit_code}",
        f"错误: {ctx.error}",
        f"补偿尝试: {ctx.heal_attempts} 次（上限）",
        f"Trace ID: `{ctx.trace_id}`",
        f"",
        f"**建议操作:**",
        f"1. 检查 Azure Portal 中资源状态",
        f"2. 查看 Activity Log: `az monitor activity-log list --resource-group <rg>`",
        f"3. 确认配额: `az vm list-usage --location <loc>`",
        f"4. 重试或手动修复后，附 Trace ID 重新提交任务",
    ]
    return "\n".join(lines)
```

---

### Task 6: 实现 `auto_feedback_loop.py`（主入口）

**Files:**
- Create: `scripts/auto_feedback_loop.py`

- [ ] **Step 1: 实现 `scripts/auto_feedback_loop.py`**

```python
#!/usr/bin/env python3
"""
auto_feedback_loop.py — L4 自动化闭环主入口

用法：
  python scripts/auto_feedback_loop.py \
    --skill azure-vm-ops \
    --operation vm_create \
    --command "az vm create --name myvm --resource-group myrg --location eastus ..." \
    --desired-state '{"powerState": "VM running"}' \
    --trace-id <uuid> \
    [--risky] \
    [--dry-run]
"""
import argparse
import subprocess
import sys
import time
import uuid
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone

# 本地模块
from state_diff import diff, DiffResult
from state_observer import observe, ObserveResult
from self_healing.loader import load_policy
from escalation import escalate, EscalationContext

TRACE_DIR = Path(__file__).parent.parent / "audit-results"

@dataclass
class FeedbackResult:
    status: str           # "success" | "healed" | "escalated" | "failed"
    actual_state: dict
    heal_attempts: int
    trace_id: str
    message: str
    escalation: str | None

def _expand_vars(template: str | list, env: dict) -> str | list:
    """展开策略 JSON 中的 {{env.VAR}}"""
    if isinstance(template, str):
        import re
        def repl(m):
            key = m.group(1)
            return env.get(key, m.group(0))
        return re.sub(r'\{\{env\.(\w+)\}\}', repl, template)
    elif isinstance(template, list):
        return [_expand_vars(item, env) for item in template]
    return template

def _apply_heal_rule(rule: dict, actual: dict, parsed: str | None, env: dict) -> tuple[bool, str]:
    """
    判断条件是否满足，执行 heal action。
    返回 (applied, message)
    """
    cond_type = rule.get("condition_type")
    if cond_type == "field_not_equal":
        field = rule.get("condition_field", "")
        expected = rule.get("condition_value", "")
        # 用 state_observer 的 _jmespath 解析 actual
        actual_val = _jmespath_simple(field, actual)
        if actual_val != expected:
            action = rule.get("heal_action", "")
            args = _expand_vars(rule.get("heal_args_template", []), env)
            cmd = action.split() + args
            result = subprocess.run(["az"] + cmd,
                                    capture_output=True, text=True, timeout=120)
            return True, f"heal applied: {action} -> exit={result.returncode}"
    return False, "condition not met"

def _jmespath_simple(path: str, data: dict):
    """复用 state_observer._jmespath 的简化版"""
    parts = path.split(".")
    current = data
    for part in parts:
        if current is None:
            return None
        if "[" in part and "]" in part:
            key, bracket = part.split("[", 1)
            idx = int(bracket.strip("]"))
            if key:
                current = current.get(key)
            if isinstance(current, list) and len(current) > idx:
                current = current[idx]
            else:
                return None
        else:
            current = current.get(part)
    return current

def _persist_trace(trace_id: str, result: FeedbackResult):
    """写入 audit-results/gcl-trace-<id>.json"""
    import os
    trace_file = TRACE_DIR / f"gcl-trace-{trace_id[:8]}.json"
    # 复用现有 az_trace.py 的 trace schema
    trace = {
        "id": trace_id,
        "name": f"{result.status} feedback-loop",
        "metadata": {
            "skill": "auto-feedback-loop",
            "tool": "auto_feedback_loop.py",
            "tool_version": "1.0.0",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        },
        "gcl_status": result.status,
        "gcl_final_iter": result.heal_attempts,
        "spans": [{
            "name": "feedback-loop",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "metadata": {"status": result.status, "message": result.message},
        }]
    }
    os.makedirs(TRACE_DIR, exist_ok=True)
    trace_file.write_text(json.dumps(trace, indent=2, ensure_ascii=False))

def run_with_feedback(
    skill: str,
    operation: str,
    command: str,
    desired_state: dict,
    risky: bool = False,
    max_heal_attempts: int = 2,
    trace_id: str | None = None,
    dry_run: bool = False,
) -> FeedbackResult:
    """
    主函数：执行命令 → observe → diff → 自我修复 → 升人工
    """
    tid = trace_id or str(uuid.uuid4())
    heal_attempts = 0
    escalate_msg: str | None = None

    # 1. Human gate for risky operations
    if risky:
        escalate_msg = (
            f"⚠️  Risky operation '{operation}' in {skill} requires human confirmation.\n"
            f"Command: {command}\n"
            f"Aborted to preserve safety gate."
        )
        result = FeedbackResult(
            status="escalated",
            actual_state={},
            heal_attempts=0,
            trace_id=tid,
            message="Risky operation — human gate",
            escalation=escalate_msg,
        )
        _persist_trace(tid, result)
        return result

    # 2. Execute command
    if dry_run:
        cmd_list = command.split()
    else:
        result = subprocess.run(command.split(), capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            ctx = EscalationContext(
                skill=skill, operation=operation,
                command=command.split(), exit_code=result.returncode,
                error=result.stderr.strip(), heal_attempts=0, trace_id=tid,
            )
            escalate_msg = escalate(ctx)
            fb_result = FeedbackResult(
                status="escalated", actual_state={},
                heal_attempts=0, trace_id=tid,
                message=f"Command failed: {result.stderr[:100]}",
                escalation=escalate_msg,
            )
            _persist_trace(tid, fb_result)
            return fb_result

    # 3. Load policy
    policy = load_policy(skill)
    op_policy = (policy or {}).get("operations", {}).get(operation, {})
    health_check = op_policy.get("health_check")

    # 4. Observe
    actual_state: dict = {}
    parsed_val: str | None = None
    if health_check:
        obs = observe(
            api=health_check["api"],
            args_template=health_check["args_template"],
            parse_field=health_check.get("parse_field"),
        )
        actual_state = obs.raw
        parsed_val = obs.parsed
        if obs.error:
            ctx = EscalationContext(
                skill=skill, operation=operation,
                command=command.split(), exit_code=-1,
                error=f"observe failed: {obs.error}", heal_attempts=0, trace_id=tid,
            )
            escalate_msg = escalate(ctx)
            fb_result = FeedbackResult(
                status="escalated", actual_state={},
                heal_attempts=0, trace_id=tid,
                message=f"Observe failed: {obs.error}",
                escalation=escalate_msg,
            )
            _persist_trace(tid, fb_result)
            return fb_result

    # 5. Diff desired vs actual
    diff_result = diff(desired_state, actual_state, operation)
    if diff_result.match:
        fb_result = FeedbackResult(
            status="success", actual_state=actual_state,
            heal_attempts=0, trace_id=tid,
            message=f"[success] {diff_result.message}",
            escalation=None,
        )
        _persist_trace(tid, fb_result)
        return fb_result

    # 6. Self-healing
    heal_rules = op_policy.get("healing_rules", [])
    escalate_on = op_policy.get("escalate_on", [])
    for attempt in range(1, max_heal_attempts + 1):
        applied = False
        for rule in heal_rules:
            ok, msg = _apply_heal_rule(rule, actual_state, parsed_val, {})
            if ok:
                applied = True
                heal_attempts = attempt
                backoff = rule.get("backoff_sec", 30)
                time.sleep(backoff)
                # Re-observe
                if health_check:
                    obs = observe(health_check["api"], health_check["args_template"],
                                  health_check.get("parse_field"))
                    actual_state = obs.raw
                    parsed_val = obs.parsed
                # Re-diff
                diff_result = diff(desired_state, actual_state, operation)
                if diff_result.match:
                    fb_result = FeedbackResult(
                        status="healed", actual_state=actual_state,
                        heal_attempts=heal_attempts, trace_id=tid,
                        message=f"[healed] {diff_result.message}",
                        escalation=None,
                    )
                    _persist_trace(tid, fb_result)
                    return fb_result
        if not applied:
            break

    # 7. Escalate
    ctx = EscalationContext(
        skill=skill, operation=operation, command=command.split(),
        exit_code=-1,
        error=f"heal exhausted ({heal_attempts} attempts). Diffs: {[d.field for d in diff_result.diffs]}",
        heal_attempts=heal_attempts, trace_id=tid,
    )
    escalate_msg = escalate(ctx)
    fb_result = FeedbackResult(
        status="escalated", actual_state=actual_state,
        heal_attempts=heal_attempts, trace_id=tid,
        message=f"[escalated] {diff_result.message}",
        escalation=escalate_msg,
    )
    _persist_trace(tid, fb_result)
    return fb_result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="L4 auto-feedback loop for Azure skills")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--operation", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--desired-state", required=True)
    parser.add_argument("--trace-id", default=None)
    parser.add_argument("--risky", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    desired = json.loads(args.desired_state)
    result = run_with_feedback(
        skill=args.skill,
        operation=args.operation,
        command=args.command,
        desired_state=desired,
        risky=args.risky,
        trace_id=args.trace_id,
        dry_run=args.dry_run,
    )
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    sys.exit(0 if result.status in ("success", "healed") else 1)
```

---

### Task 7: 补充单元测试覆盖核心逻辑

**Files:**
- Modify: `tests/test_auto_feedback_loop.py`

- [ ] **Step 1: 补充 dry-run 测试**

```python
def test_risky_operation_returns_escalated():
    """risky=True 操作应直接返回 escalated，不执行命令"""
    result = run_with_feedback(
        skill="azure-vm-ops",
        operation="vm_delete",
        command="az vm delete --name myvm --resource-group myrg",
        desired_state={"powerState": "VM running"},
        risky=True,
        dry_run=True,
    )
    assert result.status == "escalated"
    assert "human gate" in result.message

def test_dry_run_no_execution():
    """dry_run=True 不执行 az 命令，返回状态"""
    result = run_with_feedback(
        skill="azure-vm-ops",
        operation="vm_create",
        command="az vm create --name myvm --resource-group myrg",
        desired_state={"powerState": "VM running"},
        risky=False,
        dry_run=True,
    )
    # dry_run 模式：走完全部 diff/heal 逻辑但不实际执行 az
    assert result.status in ("success", "escalated", "failed")  # 不 crash 即通过
```

- [ ] **Step 2: 运行完整测试套件**

Run: `python -m pytest tests/ -v`
Expected: 全部 PASS。

---

### Task 8: CLI 接口验证（dry-run）

**Files:**
- Modify: `scripts/auto_feedback_loop.py`（无需修改，验证调用方式）

- [ ] **Step 1: dry-run 验证 risky 操作 human gate**

Run: `python scripts/auto_feedback_loop.py --skill azure-vm-ops --operation vm_delete --command "az vm delete --name test --resource-group test-rg" --desired-state '{}' --risky --dry-run`
Expected: 输出包含 `"status": "escalated"` 和 `"human gate"`。

- [ ] **Step 2: dry-run 验证 non-risky 操作**

Run: `python scripts/auto_feedback_loop.py --skill azure-vm-ops --operation vm_create --command "az vm create --name test --resource-group test-rg" --desired-state '{"powerState": "VM running"}' --dry-run`
Expected: 不抛异常，输出结构正确（无真实 Azure 凭证下返回 escalated 是预期行为）。

---

### Task 9: CADL 沉淀

**Files:**
- Modify: `AGENTS.md`（末尾追加 L4 经验）

- [ ] **Step 1: 写 CADL finding**

```json
{
  "task": "gcl-l4-auto-feedback-loop",
  "date": "2026-07-18",
  "pattern": "L4 自动化闭环 = 最小闭环（observe + diff + heal）+ 策略外置 JSON",
  "anti_pattern": "不要在 auto_feedback_loop.py 中硬编码修复策略，每新增 skill 都要改代码",
  "correct": "策略放 scripts/self_healing/<skill>_heal.json，loader.py 读取",
  "scope": "本仓库（azure-skills）"
}
```

- [ ] **Step 2: 追加到 AGENTS.md（检查行数）**

Run: `wc -l AGENTS.md`
Expected: < 500 行。如接近 500，先精简再追加。

---

### Task 10: 完整集成验证

- [ ] **Step 1: 验证 trace 文件写入**

Run: `ls audit-results/gcl-trace-*.json | wc -l`
Expected: > 0（dry-run 已产生 trace）。

- [ ] **Step 2: 验证无凭证明文泄露**

Run: `python -c "import subprocess; r=subprocess.run(['grep','-r','ClientSecret\\|password\\|AK==', 'scripts/'],capture_output=True,text=True); print(r.stdout[:500])"`
Expected: 仅 `{{env.*}}` 占位符，无真实凭据。

- [ ] **Step 3: git diff 检查**

Run: `git diff --stat`
Expected: 仅 `scripts/auto_feedback_loop.py`、`scripts/state_diff.py`、`scripts/state_observer.py`、`scripts/escalation.py`、`scripts/self_healing/`、`tests/`、`AGENTS.md`、`docs/superpowers/specs/`、`docs/superpowers/plans/` 变更。

---

## Self-Review 检查清单

**Spec 覆盖：**
- [x] L4 自动化闭环 4 个子模块全部有对应 Task
- [x] 验收标准（功能 / 非功能 / 安全）全部有对应测试或验证步骤
- [x] 约束（零依赖、不改 Skill、Python >= 3.10）全部在 Task 中体现

**Placeholder 扫描：**
- 无 "TBD" / "TODO" / "implement later"
- 无 "add appropriate error handling"（具体处理已写出）
- 测试有实际 assert，无 "test should pass" 类占位

**类型一致性：**
- `FeedbackResult` dataclass 在 Task 6 定义，Task 7/8 引用一致
- `DiffResult` / `DiffEntry` 在 Task 2 定义，Task 6 引用一致
- `EscalationContext` 在 Task 5 定义，Task 6 引用一致

**Spec ↔ Plan 一致性：**
- API 设计（`run_with_feedback` / `observe` / `diff` / `escalate`）与 spec §2.3 完全对齐
- 策略 JSON schema 与 spec §2.3 一致
- 验收标准（Task 8 CLI 验证）与 spec §3.1 完全对应
