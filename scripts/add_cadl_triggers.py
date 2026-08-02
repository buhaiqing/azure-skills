#!/usr/bin/env python3
"""批量为所有 skills 添加 CADL 触发器

CADL 触发器格式：
> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
"""
import sys
from pathlib import Path


CADL_TRIGGER = "\n> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。\n"


def add_cadl_trigger(skill_dir: Path) -> bool:
    """为单个 skill 添加 CADL 触发器，返回是否修改"""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return False

    content = skill_md.read_text(encoding="utf-8")

    # 检查是否已包含完整 CADL 触发器（不是仅仅提到 CADL）
    if "复利资产沉淀机制" in content or "复盘并沉淀可复用资产" in content:
        return False

    # 添加 CADL 触发器到文件末尾
    with open(skill_md, "a", encoding="utf-8") as f:
        f.write(CADL_TRIGGER)

    return True


def main():
    repo_root = Path(__file__).parent.parent
    skills_dir = repo_root

    # 查找所有 azure-*-ops 目录
    skill_dirs = sorted(skills_dir.glob("azure-*-ops"))

    if not skill_dirs:
        print("未找到 azure-*-ops 目录")
        return 1

    modified_count = 0
    skipped_count = 0

    for skill_dir in skill_dirs:
        if not skill_dir.is_dir():
            continue

        if add_cadl_trigger(skill_dir):
            print(f"✓ {skill_dir.name}")
            modified_count += 1
        else:
            print(f"- {skill_dir.name} (已存在或无需修改)")
            skipped_count += 1

    print(f"\n总计: {modified_count} 个已修改, {skipped_count} 个跳过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
