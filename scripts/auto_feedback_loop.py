#!/usr/bin/env python3
"""
auto_feedback_loop.py — L4 自动化闭环主入口

用法：
  python scripts/auto_feedback_loop.py \\
    --skill azure-vm-ops \\
    --operation vm_create \\
    --command "az vm create --name myvm --resource-group myrg --location eastus ..." \\
    --desired-state '{"powerState": "VM running"}' \\
    [--risky] [--dry-run] [--trace-id <uuid>]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# 本地模块（scripts/ 目录）
from state_diff import diff, DiffResult
from state_observer import observe, ObserveResult
from self_healing.loader import load_policy
from escalation import escalate, EscalationContext


TRACE_DIR = Path(__file__).parent.parent / "audit-results"


@dataclass
class FeedbackResult:
    status: str  # "success" | "healed" | "escalated" | "failed"
    actual_state: dict
    heal_attempts: int
    trace_id: str
    message: str
    escalation: Optional[str]


# ------------------------------------------------------------------
# 内部工具
# ------------------------------------------------------------------

def _jmespath_simple(path: str, data: dict) -> Any:
    """复用 state_observer._jmespath 的简化版"""
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


def _expand_vars(template: str | list, env: dict) -> str | list:
    """展开策略 JSON 中的 {{env.VAR}} 占位符"""
    if isinstance(template, str):
        def repl(m):
            key = m.group(1)
            return env.get(key, m.group(0))
        return re.sub(r'\{\{env\.(\w+)\}\}', repl, template)
    elif isinstance(template, list):
        return [_expand_vars(item, env) for item in template]
    return template


def _apply_heal_rule(rule: dict, actual: dict, parsed: Optional[str], env: dict) -> tuple[bool, str]:
    """判断条件是否满足，满足则执行 heal action。返回 (applied, message)"""
    cond_type = rule.get("condition_type")
    if cond_type == "field_not_equal":
        field = rule.get("condition_field", "")
        expected = rule.get("condition_value", "")
        actual_val = _jmespath_simple(field, actual)
        if actual_val != expected:
            action = rule.get("heal_action", "")
            args = _expand_vars(rule.get("heal_args_template", []), env)
            cmd = action.split() + args
            try:
                result = subprocess.run(
                    ["az"] + cmd,
                    capture_output=True, text=True, timeout=120,
                )
                return True, f"heal applied: {action} -> exit={result.returncode}"
            except Exception as exc:
                return True, f"heal applied but failed: {exc}"
    return False, "condition not met"


def _persist_trace(trace_id: str, result: FeedbackResult):
    """写入 audit-results/gcl-trace-<id8>.json，复用 az_trace.py 的 schema"""
    os.makedirs(TRACE_DIR, exist_ok=True)
    trace_file = TRACE_DIR / f"gcl-trace-{trace_id[:8]}.json"
    trace = {
        "id": trace_id,
        "name": f"feedback-loop {result.status}",
        "metadata": {
            "skill": "auto-feedback-loop",
            "tool": "auto_feedback_loop.py",
            "tool_version": "1.0.0",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "os": os.name,
        },
        "gcl_status": result.status,
        "gcl_final_iter": result.heal_attempts,
        "spans": [{
            "name": "feedback-loop",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "status": result.status,
                "message": result.message,
                "heal_attempts": result.heal_attempts,
            },
        }]
    }
    trace_file.write_text(json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------
# 主函数
# ------------------------------------------------------------------

def run_with_feedback(
    skill: str,
    operation: str,
    command: str,
    desired_state: dict,
    risky: bool = False,
    max_heal_attempts: int = 2,
    trace_id: Optional[str] = None,
    dry_run: bool = False,
) -> FeedbackResult:
    """
    完整 L4 闭环：执行 → observe → diff → 自我修复 → 升人工
    """
    tid = trace_id or str(uuid.uuid4())
    heal_attempts = 0
    escalation_msg: Optional[str] = None

    # 1. Human gate — risky 操作不自动执行
    if risky:
        escalation_msg = (
            f"⚠️  Risky operation '{operation}' in {skill} requires human confirmation.\n"
            f"Command: {command}\n"
            f"Aborted to preserve safety gate."
        )
        result = FeedbackResult(
            status="escalated",
            actual_state={},
            heal_attempts=0,
            trace_id=tid,
            message="Risky operation — human gate enforced",
            escalation=escalation_msg,
        )
        _persist_trace(tid, result)
        return result

    # 2. 执行命令
    cmd_list = command.split()
    if not dry_run:
        exec_result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if exec_result.returncode != 0:
            ctx = EscalationContext(
                skill=skill,
                operation=operation,
                command=command,
                exit_code=exec_result.returncode,
                error=exec_result.stderr.strip() or f"exit {exec_result.returncode}",
                heal_attempts=0,
                trace_id=tid,
            )
            escalation_msg = escalate(ctx)
            fb_result = FeedbackResult(
                status="escalated",
                actual_state={},
                heal_attempts=0,
                trace_id=tid,
                message=f"Command failed: {exec_result.stderr[:120].strip()}",
                escalation=escalation_msg,
            )
            _persist_trace(tid, fb_result)
            return fb_result

    # 3. 加载策略
    policy = load_policy(skill)
    op_policy = (policy or {}).get("operations", {}).get(operation, {})
    health_check = op_policy.get("health_check")

    # 4. Observe — 获取资源实际状态
    actual_state: dict = {}
    parsed_val: Optional[str] = None
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
                command=command, exit_code=-1,
                error=f"observe failed: {obs.error}",
                heal_attempts=0, trace_id=tid,
            )
            escalation_msg = escalate(ctx)
            fb_result = FeedbackResult(
                status="escalated",
                actual_state={},
                heal_attempts=0,
                trace_id=tid,
                message=f"Observe failed: {obs.error}",
                escalation=escalation_msg,
            )
            _persist_trace(tid, fb_result)
            return fb_result

    # 5. Diff — 比对 desired vs actual
    diff_result = diff(desired_state, actual_state, operation)
    if diff_result.match:
        fb_result = FeedbackResult(
            status="success",
            actual_state=actual_state,
            heal_attempts=0,
            trace_id=tid,
            message=f"[success] {diff_result.message}",
            escalation=None,
        )
        _persist_trace(tid, fb_result)
        return fb_result

    # 6. Self-healing
    heal_rules = op_policy.get("healing_rules", [])
    if not heal_rules:
        # 有 diff 但无修复策略，升人工
        ctx = EscalationContext(
            skill=skill, operation=operation,
            command=command, exit_code=-1,
            error=f"state mismatch, no healing strategy: {[d.field for d in diff_result.diffs]}",
            heal_attempts=0, trace_id=tid,
        )
        escalation_msg = escalate(ctx)
        fb_result = FeedbackResult(
            status="escalated",
            actual_state=actual_state,
            heal_attempts=0,
            trace_id=tid,
            message=f"[escalated] {diff_result.message} (no heal policy)",
            escalation=escalation_msg,
        )
        _persist_trace(tid, fb_result)
        return fb_result

    for attempt in range(1, max_heal_attempts + 1):
        applied_any = False
        for rule in heal_rules:
            ok, msg = _apply_heal_rule(rule, actual_state, parsed_val, {})
            if ok:
                applied_any = True
                heal_attempts = attempt
                backoff = rule.get("backoff_sec", 30)
                time.sleep(backoff)
                # Re-observe
                if health_check:
                    obs = observe(
                        health_check["api"],
                        health_check["args_template"],
                        health_check.get("parse_field"),
                    )
                    actual_state = obs.raw
                    parsed_val = obs.parsed
                    if obs.error:
                        break
                # Re-diff
                diff_result = diff(desired_state, actual_state, operation)
                if diff_result.match:
                    fb_result = FeedbackResult(
                        status="healed",
                        actual_state=actual_state,
                        heal_attempts=heal_attempts,
                        trace_id=tid,
                        message=f"[healed] {diff_result.message}",
                        escalation=None,
                    )
                    _persist_trace(tid, fb_result)
                    return fb_result
        if not applied_any:
            break

    # 7. 补偿耗尽，升人工
    ctx = EscalationContext(
        skill=skill, operation=operation,
        command=command, exit_code=-1,
        error=f"heal exhausted ({heal_attempts} attempts). "
              f"Mismatched fields: {[d.field for d in diff_result.diffs]}",
        heal_attempts=heal_attempts, trace_id=tid,
    )
    escalation_msg = escalate(ctx)
    fb_result = FeedbackResult(
        status="escalated",
        actual_state=actual_state,
        heal_attempts=heal_attempts,
        trace_id=tid,
        message=f"[escalated] {diff_result.message}",
        escalation=escalation_msg,
    )
    _persist_trace(tid, fb_result)
    return fb_result


# ------------------------------------------------------------------
# CLI 入口
# ------------------------------------------------------------------

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
