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
import shlex
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
from state_observer import observe, ObserveResult, observe_cost, observe_budget, CostObservation
from self_healing.loader import load_policy
from escalation import escalate, EscalationContext
from report_finding import report_finding
from risk_tiers import apply_tier_gates


TRACE_DIR = Path(__file__).parent.parent / "audit-results"


@dataclass
class FeedbackResult:
    status: str  # "success" | "healed" | "escalated" | "failed"
    actual_state: dict
    heal_attempts: int
    trace_id: str
    message: str
    escalation: Optional[str]
    cost_observation: Optional[dict] = None  # CostObserver result, if enabled


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
    """展开策略 JSON 中的 {{env.VAR}} 占位符。未定义的变量抛 ValueError。"""
    if isinstance(template, str):
        def repl(m):
            key = m.group(1)
            if key not in env:
                raise ValueError(
                    f"Undefined variable: {{env.{key}}} — "
                    f"must be set in environment before execution"
                )
            return env[key]
        return re.sub(r'\{\{env\.(\w+)\}\}', repl, template)
    elif isinstance(template, list):
        return [_expand_vars(item, env) for item in template]
    return template


def _heal_argv(action: str, args: list) -> list[str]:
    """Build az argv; prefer args_template; never double-prefix ``az``."""
    tokens: list[str] = [str(a) for a in args] if args else action.split()
    if tokens and tokens[0] == "az":
        tokens = tokens[1:]
    return ["az"] + tokens


def _apply_heal_rule(rule: dict, actual: dict, parsed: Optional[str], env: dict,
                     trend_history: Optional[list[dict]] = None,
                     *, dry_run: bool = False) -> tuple[bool, str]:
    """判断条件是否满足，满足则执行 heal action。返回 (applied, message)
    
    condition_type 支持：
      - field_not_equal: 字段值不等于 expected
      - field_above_threshold: 字段值 > threshold_value
      - field_below_threshold: 字段值 < threshold_value
      - trend_increasing: 连续 trend_window 次观测值递增
      - rate_of_change: 字段值变化率 > threshold_value (最近两次观测)
    """
    cond_type = rule.get("condition_type")
    field = rule.get("condition_field", "")
    actual_val = _jmespath_simple(field, actual)

    condition_met = False

    if cond_type == "field_not_equal":
        expected = rule.get("condition_value", "")
        condition_met = (actual_val != expected)

    elif cond_type == "field_above_threshold":
        threshold = rule.get("threshold_value", 0)
        try:
            num_val = float(actual_val) if actual_val is not None else 0
            condition_met = num_val > threshold
        except (TypeError, ValueError):
            condition_met = False

    elif cond_type == "field_below_threshold":
        threshold = rule.get("threshold_value", 0)
        try:
            num_val = float(actual_val) if actual_val is not None else 0
            condition_met = num_val < threshold
        except (TypeError, ValueError):
            condition_met = False

    elif cond_type == "trend_increasing":
        window = rule.get("trend_window", 3)
        if trend_history and len(trend_history) >= window:
            # 检查最近 window 次观测值是否单调递增
            vals = []
            for h in trend_history[-window:]:
                v = _jmespath_simple(field, h.get("state", {}))
                try:
                    vals.append(float(v) if v is not None else 0)
                except (TypeError, ValueError):
                    vals.append(0)
            condition_met = all(vals[i] < vals[i + 1] for i in range(len(vals) - 1))
        else:
            condition_met = False

    elif cond_type == "rate_of_change":
        threshold = rule.get("threshold_value", 0.5)
        if trend_history and len(trend_history) >= 2:
            last_two = trend_history[-2:]
            v0 = _jmespath_simple(field, last_two[0].get("state", {}))
            v1 = _jmespath_simple(field, last_two[1].get("state", {}))
            try:
                v0_f, v1_f = float(v0) if v0 is not None else 0, float(v1) if v1 is not None else 0
                if v0_f != 0:
                    change_rate = abs((v1_f - v0_f) / v0_f)
                    condition_met = change_rate > threshold
            except (TypeError, ValueError):
                condition_met = False
        else:
            condition_met = False

    if not condition_met:
        return False, "condition not met"

    action = rule.get("heal_action", "")
    raw_args = _expand_vars(rule.get("heal_args_template", []), env)
    args_list = raw_args if isinstance(raw_args, list) else []
    cmd = _heal_argv(action, args_list)
    if dry_run:
        return True, f"heal planned (dry-run): {' '.join(cmd)}"
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return True, f"heal applied: {' '.join(cmd)}"
        err = (result.stderr or result.stdout or "").strip()[:200]
        return False, f"heal failed exit={result.returncode}: {err}"
    except Exception as exc:
        return False, f"heal exception: {exc}"


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
    observe_cost_enabled: bool = False,
    subscription_id: Optional[str] = None,
) -> FeedbackResult:
    """
    完整 L4 闭环：执行 → observe → diff → 自我修复 → 升人工

    Args:
        observe_cost_enabled: 若为 True，闭环完成后自动查询订阅成本
        subscription_id: Azure 订阅 ID（observe_cost_enabled=True 时必须提供）
    """
    tid = trace_id or str(uuid.uuid4())
    heal_attempts = 0
    escalation_msg: Optional[str] = None

    # Risk tier gates (MS L400) — R2 / human_confirm forces risky path
    gates = apply_tier_gates(skill, operation, risky_flag=risky)
    if gates["force_risky"]:
        risky = True
    if not gates["auto_heal"]:
        max_heal_attempts = 0
    else:
        # Do not use `or` — caller may pass explicit 0 to disable heal
        max_heal_attempts = min(max_heal_attempts, gates["max_heal_attempts"])

    def _finalize(fb: FeedbackResult) -> FeedbackResult:
        """统一后处理：persist trace + 可选成本观测"""
        _persist_trace(tid, fb)
        if observe_cost_enabled and subscription_id:
            fb = _observe_and_attach_cost(fb, subscription_id, skill, operation)
        return fb

    # 1. Human gate — risky / R2 操作不自动执行
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
        return _finalize(result)

    # dry_run: no az execute / observe / heal side effects (MS L400 safety)
    if dry_run:
        gcl_note = ""
        if gates.get("gcl_required"):
            gcl_note = " [gcl_required: wrap with gcl_runner for production]"
        return _finalize(FeedbackResult(
            status="planned",
            actual_state={},
            heal_attempts=0,
            trace_id=tid,
            message=(
                f"[dry-run] planned {skill}/{operation} tier={gates['tier']}; "
                f"no az calls{gcl_note}"
            ),
            escalation=None,
        ))

    # 2. 执行命令
    cmd_list = shlex.split(command)
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
                heal_history=[],
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
            report_finding(skill=skill, operation=operation,
                          failure_type="command_failed",
                          context={"exit_code": exec_result.returncode,
                                   "stderr": exec_result.stderr[:200]},
                          trace_id=tid)
            return _finalize(fb_result)

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
                heal_history=[],
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
            report_finding(skill=skill, operation=operation,
                          failure_type="observe_failed",
                          context={"error": obs.error},
                          trace_id=tid)
            return _finalize(fb_result)

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
        return _finalize(fb_result)

    # 6. Self-healing
    heal_rules = op_policy.get("healing_rules", [])
    if not heal_rules:
        # 有 diff 但无修复策略，升人工
        ctx = EscalationContext(
            skill=skill, operation=operation,
            command=command, exit_code=-1,
            error=f"state mismatch, no healing strategy: {[d.field for d in diff_result.diffs]}",
            heal_attempts=0, trace_id=tid,
            heal_history=[],
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
        report_finding(skill=skill, operation=operation,
                      failure_type="no_heal_policy",
                      context={"diff_fields": [d.field for d in diff_result.diffs]},
                      trace_id=tid)
        return _finalize(fb_result)

    heal_history: list = []
    trend_history: list = []
    for attempt in range(1, max_heal_attempts + 1):
        applied_any = False
        for rule in heal_rules:
            rule_name = rule.get("heal_action", "unknown")
            ok, msg = _apply_heal_rule(rule, actual_state, parsed_val, {},
                                        trend_history if trend_history else None,
                                        dry_run=False)
            heal_history.append({
                "attempt": attempt,
                "rule_name": rule_name,
                "action": rule_name,
                "ok": ok,
                "error": msg if not ok else None,
            })
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
                    trend_history.append({"state": actual_state, "parsed": parsed_val})
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
                    return _finalize(fb_result)
        if not applied_any:
            break

    # 7. 补偿耗尽，升人工
    ctx = EscalationContext(
        skill=skill, operation=operation,
        command=command, exit_code=-1,
        error=f"heal exhausted ({heal_attempts} attempts). "
              f"Mismatched fields: {[d.field for d in diff_result.diffs]}",
        heal_attempts=heal_attempts, trace_id=tid,
        heal_history=heal_history,
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
    report_finding(skill=skill, operation=operation,
                  failure_type="heal_exhausted",
                  context={"diff_fields": [d.field for d in diff_result.diffs],
                           "heal_attempts": heal_attempts},
                  trace_id=tid)
    return _finalize(fb_result)


# ------------------------------------------------------------------
# CostObserver 集成
# ------------------------------------------------------------------

def _observe_and_attach_cost(
    result: FeedbackResult,
    subscription_id: Optional[str],
    skill: str,
    operation: str,
) -> FeedbackResult:
    """观测成本并附加到 FeedbackResult。失败时不阻塞闭环结果。"""
    if not subscription_id:
        result.message += " (cost: no subscription_id)"
        return result

    try:
        cost_obs = observe_cost(subscription_id)
        result.cost_observation = {
            "current_cost": cost_obs.current_cost,
            "previous_cost": cost_obs.previous_cost,
            "cost_change_pct": round(cost_obs.cost_change_pct, 2),
            "error": cost_obs.error,
        }
        if cost_obs.error:
            result.message += f" (cost observe failed: {cost_obs.error})"
        else:
            change = cost_obs.cost_change_pct
            if change > 20:
                result.message += f" (⚠️ cost surged {change:.1f}% — consider SKU downgrade or idle resource cleanup)"
            elif change > 10:
                result.message += f" (cost up {change:.1f}% — monitoring)"
            else:
                result.message += f" (cost change: {change:+.1f}%)"
    except Exception as exc:
        result.cost_observation = {
            "current_cost": 0, "previous_cost": 0,
            "cost_change_pct": 0, "error": str(exc),
        }
        result.message += f" (cost error: {exc})"

    return result


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
    parser.add_argument("--observe-cost", action="store_true",
                        help="Enable CostObserver: query subscription cost after loop")
    parser.add_argument("--subscription-id", default=None,
                        help="Azure subscription ID for cost observation")
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
        observe_cost_enabled=args.observe_cost,
        subscription_id=args.subscription_id,
    )
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    sys.exit(0 if result.status in ("success", "healed", "planned") else 1)
