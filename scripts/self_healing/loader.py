#!/usr/bin/env python3
"""策略加载器 — 无外部依赖"""
import json
from pathlib import Path
from typing import Optional


REGISTRY_PATH = Path(__file__).parent / "registry.json"


def load_registry(path: str | Path | None = None) -> dict:
    """加载策略注册表"""
    p = Path(path) if path else REGISTRY_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def load_policy(skill_name: str, registry_path: str | Path | None = None) -> Optional[dict]:
    """
    根据 skill_name 从注册表找到对应策略文件并加载。
    返回 None 如果 skill 未注册。
    """
    registry = load_registry(registry_path)
    skill_map = registry.get("skills", {})
    policy_file = skill_map.get(skill_name)
    if not policy_file:
        return None
    policy_path = Path(__file__).parent / policy_file
    if not policy_path.exists():
        return None
    return json.loads(policy_path.read_text(encoding="utf-8"))
