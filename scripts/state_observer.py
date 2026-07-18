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
