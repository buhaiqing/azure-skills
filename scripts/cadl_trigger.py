#!/usr/bin/env python3
"""CADL 触发器自动化注入工具

为所有 azure-*-ops/SKILL.md 文件注入 CADL（复利资产沉淀机制）触发钩子。
确保每个 skill 完成后都会触发 CADL 闭环，沉淀可复用资产。

用法:
    python scripts/cadl_trigger.py              # 扫描并注入缺失的 CADL 钩子
    python scripts/cadl_trigger.py --check      # 仅检查，不修改文件
    python scripts/cadl_trigger.py --dry-run    # 显示将要注入的文件，不实际修改
"""
import argparse
import re
from pathlib import Path
from typing import List, Tuple

# CADL 触发钩子标准文本
CADL_HOOK = "> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。"


def find_skill_files(root: Path) -> List[Path]:
    """查找所有 azure-*-ops/SKILL.md 文件"""
    pattern = re.compile(r"^azure-.*-ops$")
    skill_files = []
    
    for item in root.iterdir():
        if item.is_dir() and pattern.match(item.name):
            skill_md = item / "SKILL.md"
            if skill_md.exists():
                skill_files.append(skill_md)
    
    return sorted(skill_files)


def check_cadl_hook(skill_file: Path) -> bool:
    """检查 SKILL.md 是否已包含 CADL 钩子"""
    content = skill_file.read_text(encoding="utf-8")
    return "复利资产沉淀机制" in content or "CADL" in content


def inject_cadl_hook(skill_file: Path, dry_run: bool = False) -> bool:
    """向 SKILL.md 末尾注入 CADL 钩子
    
    Returns:
        True if hook was injected (or would be in dry-run mode)
        False if hook already exists
    """
    if check_cadl_hook(skill_file):
        return False
    
    content = skill_file.read_text(encoding="utf-8")
    
    # 确保文件末尾有换行
    if not content.endswith("\n"):
        content += "\n"
    
    # 添加 CADL 钩子
    new_content = content + "\n" + CADL_HOOK + "\n"
    
    if not dry_run:
        skill_file.write_text(new_content, encoding="utf-8")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="CADL 触发器自动化注入工具")
    parser.add_argument("--check", action="store_true", help="仅检查，不修改文件")
    parser.add_argument("--dry-run", action="store_true", help="显示将要注入的文件，不实际修改")
    parser.add_argument("--root", type=Path, default=Path(__file__).parent.parent, help="仓库根目录")
    args = parser.parse_args()
    
    skill_files = find_skill_files(args.root)
    
    if not skill_files:
        print("未找到任何 azure-*-ops/SKILL.md 文件")
        return 1
    
    injected = []
    skipped = []
    
    for skill_file in skill_files:
        has_hook = check_cadl_hook(skill_file)
        
        if has_hook:
            skipped.append(skill_file)
        else:
            injected.append(skill_file)
            if not args.check and not args.dry_run:
                inject_cadl_hook(skill_file, dry_run=False)
    
    # 输出报告
    print(f"扫描完成：找到 {len(skill_files)} 个 skill 文件")
    print(f"  已有 CADL 钩子：{len(skipped)} 个")
    print(f"  缺失 CADL 钩子：{len(injected)} 个")
    
    if args.check:
        if injected:
            print("\n缺失 CADL 钩子的文件：")
            for f in injected:
                print(f"  - {f.relative_to(args.root)}")
            return 1
        else:
            print("\n✓ 所有 skill 文件均已包含 CADL 钩子")
            return 0
    
    if args.dry_run:
        if injected:
            print("\n将注入 CADL 钩子的文件（dry-run 模式）：")
            for f in injected:
                print(f"  - {f.relative_to(args.root)}")
        else:
            print("\n无需注入")
        return 0
    
    # 实际注入模式
    if injected:
        print(f"\n✓ 已为 {len(injected)} 个文件注入 CADL 钩子")
        for f in injected:
            print(f"  - {f.relative_to(args.root)}")
    else:
        print("\n无需注入，所有文件已包含 CADL 钩子")
    
    return 0


if __name__ == "__main__":
    exit(main())
