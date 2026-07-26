#!/usr/bin/env python3
"""
state_observer.py — 调用 Azure CLI 获取资源实际状态

通过 subprocess 执行 az 命令，返回原始 JSON 和指定 JMESPath 字段值。
无外部依赖（仅 stdlib）。
"""
import json
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ObserveResult:
    raw: dict[str, Any]
    parsed: Optional[str]
    elapsed_sec: float
    error: Optional[str]


def _jmespath_simple(path: str, data: dict) -> Any:
    """简化 JMESPath：支持 "field" / "a.b" / "list[0].field" 形式"""
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


def observe(
    api: str,
    args_template: list[str],
    parse_field: Optional[str] = None,
    env: Optional[dict] = None,
    timeout: int = 30,
) -> ObserveResult:
    """
    通过 subprocess 执行 az 命令，返回观察结果。

    Args:
        api: az 子命令描述（如 "az vm get-instance-view"）
        args_template: 完整 az 参数列表
        parse_field: JMESPath 字符串（如 "statuses[1].displayStatus"）
        env: 额外环境变量
        timeout: 命令超时秒数
    """
    cmd = ["az"] + args_template
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env or None,
        )
        elapsed = time.monotonic() - start
        if result.returncode != 0:
            return ObserveResult(
                raw={}, parsed=None, elapsed_sec=elapsed,
                error=result.stderr.strip() or f"exit {result.returncode}",
            )
        try:
            raw = json.loads(result.stdout)
        except json.JSONDecodeError:
            return ObserveResult(
                raw={}, parsed=None, elapsed_sec=elapsed,
                error="invalid json output",
            )
        parsed = _jmespath_simple(parse_field, raw) if parse_field else None
        return ObserveResult(raw=raw, parsed=parsed, elapsed_sec=elapsed, error=None)
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return ObserveResult(raw={}, parsed=None, elapsed_sec=elapsed, error=f"timeout ({timeout}s)")
    except Exception as exc:
        elapsed = time.monotonic() - start
        return ObserveResult(raw={}, parsed=None, elapsed_sec=elapsed, error=str(exc))


# ------------------------------------------------------------------
# CostObserver — 成本指标观测扩展
# ------------------------------------------------------------------

COST_OBSERVER_ENABLED = True


@dataclass
class CostObservation:
    """成本观测结果"""
    current_cost: float
    previous_cost: float
    cost_change_pct: float
    budget_consumption_pct: Optional[float] = None
    ri_utilization_pct: Optional[float] = None
    error: Optional[str] = None


def observe_cost(
    subscription_id: str,
    scope: Optional[str] = None,
    days: int = 30,
) -> CostObservation:
    """
    观测订阅级别的成本数据，返回当前周期与上周期对比。

    使用 `az costmanagement query` 查询当月和上月成本。
    需要 Cost Management Reader 角色。
    """
    if not COST_OBSERVER_ENABLED:
        return CostObservation(
            current_cost=0.0, previous_cost=0.0,
            cost_change_pct=0.0,
            error="CostObserver disabled",
        )

    scope = scope or f"/subscriptions/{subscription_id}"

    try:
        # 当月成本
        current_result = subprocess.run(
            ["az", "costmanagement", "query", "--scope", scope,
             "--timeframe", "MonthToDate", "--output", "json"],
            capture_output=True, text=True, timeout=60,
        )
        if current_result.returncode != 0:
            return CostObservation(
                current_cost=0.0, previous_cost=0.0,
                cost_change_pct=0.0,
                error=f"current month query failed: {current_result.stderr.strip()}",
            )
        current_data = json.loads(current_result.stdout)

        # 上月成本
        previous_result = subprocess.run(
            ["az", "costmanagement", "query", "--scope", scope,
             "--timeframe", "TheLastBillingMonth", "--output", "json"],
            capture_output=True, text=True, timeout=60,
        )
        if previous_result.returncode != 0:
            return CostObservation(
                current_cost=0.0, previous_cost=0.0,
                cost_change_pct=0.0,
                error=f"previous month query failed: {previous_result.stderr.strip()}",
            )
        previous_data = json.loads(previous_result.stdout)

        # 提取成本值（行总计）
        def _extract_cost(data: dict) -> float:
            try:
                rows = data.get("properties", {}).get("rows", [])
                if rows:
                    return float(rows[0][0])
            except (IndexError, TypeError, ValueError):
                pass
            return 0.0

        current_cost = _extract_cost(current_data)
        previous_cost = _extract_cost(previous_data)
        cost_change_pct = ((current_cost - previous_cost) / previous_cost * 100
                           if previous_cost > 0 else 0.0)

        return CostObservation(
            current_cost=current_cost,
            previous_cost=previous_cost,
            cost_change_pct=cost_change_pct,
        )
    except subprocess.TimeoutExpired:
        return CostObservation(
            current_cost=0.0, previous_cost=0.0,
            cost_change_pct=0.0, error="cost query timeout (60s)",
        )
    except Exception as exc:
        return CostObservation(
            current_cost=0.0, previous_cost=0.0,
            cost_change_pct=0.0, error=str(exc),
        )


def observe_budget(
    subscription_id: str,
    budget_name: str,
) -> CostObservation:
    """
    观测指定预算的消耗情况。
    """
    try:
        result = subprocess.run(
            ["az", "consumption", "budget", "show",
             "--budget-name", budget_name,
             "--scope", f"/subscriptions/{subscription_id}",
             "--output", "json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return CostObservation(
                current_cost=0.0, previous_cost=0.0,
                cost_change_pct=0.0,
                error=f"budget query failed: {result.stderr.strip()}",
            )
        data = json.loads(result.stdout)
        current_spend = float(data.get("currentSpend", {}).get("amount", 0))
        amount = float(data.get("amount", 1))
        consumption_pct = (current_spend / amount * 100) if amount > 0 else 0.0

        return CostObservation(
            current_cost=current_spend,
            previous_cost=0.0,
            cost_change_pct=0.0,
            budget_consumption_pct=consumption_pct,
        )
    except Exception as exc:
        return CostObservation(
            current_cost=0.0, previous_cost=0.0,
            cost_change_pct=0.0, error=str(exc),
        )
