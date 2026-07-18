#!/usr/bin/env python3
"""
state_diff.py — desired vs actual state 比对

支持两种比对模式：
1. 简单 key 比对：desired dict 的每个 key 必须存在于 actual，
   且值必须相等
2. JMESPath-like 路径比对：key 形如 "list[0].field"，
   从 actual 中提取对应路径的值再比对
"""
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


def _jmespath_simple(path: str, data: dict) -> Any:
    """
    简化 JMESPath 实现，支持：
    - 顶层 field: "foo"
    - 嵌套 field: "a.b"
    - 数组下标: "list[0].field" / "list[0]"
    """
    parts = path.split(".")
    current: Any = data
    for part in parts:
        if current is None:
            return None
        # 处理 [n] 下标
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


def diff(desired: dict, actual: dict, operation: str) -> DiffResult:
    """
    比对 desired 和 actual 字典。
    - desired 中的每个 key 在 actual 中必须存在且值相等（支持 JMESPath 路径）
    """
    diffs: list[DiffEntry] = []
    for key, desired_val in desired.items():
        # 判断是否为 JMESPath 路径（包含 . 或 [）
        if "." in key or "[" in key:
            actual_val = _jmespath_simple(key, actual)
        else:
            actual_val = actual.get(key)

        if actual_val is None and desired_val is not None:
            diffs.append(DiffEntry(field=key, desired=desired_val, actual=None))
        elif actual_val != desired_val:
            diffs.append(DiffEntry(field=key, desired=desired_val, actual=actual_val))

    match = len(diffs) == 0
    if match:
        msg = f"[diff] operation={operation} — all fields match"
    else:
        fields = ", ".join(d.field for d in diffs)
        msg = f"[diff] operation={operation} — mismatched fields: {fields}"
    return DiffResult(match=match, diffs=diffs, message=msg)
