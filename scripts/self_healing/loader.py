#!/usr/bin/env python3
"""策略加载器 — 无外部依赖

支持两种模式：
1. 注册表模式：从 registry.json 读取 skill → policy 映射
2. 自动发现：扫描目录中的 *_heal.json 文件（当 registry.json 缺失或不完整时）
"""
import json
from pathlib import Path
from typing import Optional


REGISTRY_PATH = Path(__file__).parent / "registry.json"
POLICY_DIR = Path(__file__).parent


def discover_policies(policy_dir: str | Path | None = None) -> dict[str, str]:
    """扫描目录中的所有 *_heal.json 文件，返回 {skill_name: filename} 映射。
    
    命名约定：{short_name}_heal.json → azure-{short_name}-ops
    例如：vm_heal.json → azure-vm-ops
    """
    p = Path(policy_dir) if policy_dir else POLICY_DIR
    if not p.exists():
        return {}
    
    discovered = {}
    for heal_file in p.glob("*_heal.json"):
        # 提取 short name：去掉 _heal.json 后缀
        short_name = heal_file.stem.replace("_heal", "")
        # 转换为完整 skill name：azure-{short_name}-ops
        skill_name = f"azure-{short_name}-ops"
        discovered[skill_name] = heal_file.name
    
    return discovered

def load_registry(path: str | Path | None = None) -> dict:
    """加载策略注册表。如果文件不存在，返回空结构。"""
    p = Path(path) if path else REGISTRY_PATH
    if not p.exists():
        return {"skills": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def rebuild_registry(policy_dir: str | Path | None = None, 
                     registry_path: str | Path | None = None) -> dict:
    """基于自动发现重建 registry.json。
    
    保留现有 registry.json 中的其他字段（如 metadata），只更新 skills 映射。
    返回新的 registry 内容。
    """
    reg_path = Path(registry_path) if registry_path else REGISTRY_PATH
    
    # 读取现有 registry（如果存在）
    existing = load_registry(reg_path)
    
    # 自动发现所有策略文件
    discovered = discover_policies(policy_dir)
    
    # 合并：保留现有映射，添加新发现的
    existing_skills = existing.get("skills", {})
    existing_skills.update(discovered)
    existing["skills"] = existing_skills
    
    # 写回 registry.json
    reg_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    
    return existing


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
