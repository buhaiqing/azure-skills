#!/usr/bin/env python3
"""TE (Token Efficiency) 检查器 — 自动化 TE-1~TE-7 规则验证

C-6 复利资产：将 TE 自检清单固化为可执行脚本，确保每次 skill 更新都通过 TE 门禁。

用法:
    python scripts/te_check.py azure-vm-ops                    # 检查单个 skill
    python scripts/te_check.py                                  # 检查所有 skills
"""
import argparse
import re
import sys
from pathlib import Path
from typing import List


class TEViolation:
    def __init__(self, rule: str, file: str, line: int, message: str, fixable: bool = False):
        self.rule = rule
        self.file = file
        self.line = line
        self.message = message
        self.fixable = fixable
    
    def __str__(self):
        fixable_mark = " [FIXABLE]" if self.fixable else ""
        return f"{self.rule} @ {self.file}:{self.line}{fixable_mark}\n  {self.message}"


def check_te1_static_tables(skill_dir: Path) -> List[TEViolation]:
    """TE-1: API 查询 > 静态表格 — 检测硬编码的版本/配额信息"""
    violations = []
    skill_md = skill_dir / "SKILL.md"
    
    if not skill_md.exists():
        return violations
    
    content = skill_md.read_text(encoding="utf-8")
    lines = content.split("\n")
    
    # 检测可能的硬编码版本/配额模式（排除 metadata frontmatter）
    in_frontmatter = False
    patterns = [
        (r"version\s*[:=]\s*['\"]?\d+[\.\-]\d+", "硬编码版本号，应使用 az 命令查询"),  # matches 1.0 or 2024-01
        (r"quota\s*[:=]\s*\d+", "硬编码配额，应使用 az 命令查询"),
    ]
    
    for i, line in enumerate(lines, 1):
        # Track frontmatter boundaries
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        
        # Skip frontmatter (metadata version is OK)
        if in_frontmatter:
            continue
        
        for pattern, msg in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append(TEViolation("TE-1", str(skill_md.relative_to(skill_dir.parent)), i, msg))
    
    return violations


def check_te2_docstrings(skill_dir: Path) -> List[TEViolation]:
    """TE-2: 省略不必要的 docstring — 检测代码块中的函数级说明"""
    violations = []
    skill_md = skill_dir / "SKILL.md"
    
    if not skill_md.exists():
        return violations
    
    content = skill_md.read_text(encoding="utf-8")
    lines = content.split("\n")
    
    # 检测代码块中的 Python docstring（过度详细）
    in_code_block = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        
        if in_code_block and '"""' in line:
            violations.append(TEViolation("TE-2", str(skill_md.relative_to(skill_dir.parent)), i, 
                                         "代码块中包含 docstring，应省略"))
    
    return violations


def check_te3_error_tables(skill_dir: Path) -> List[TEViolation]:
    """TE-3: 紧凑错误表 — 每行 1 个错误码，≤3 列"""
    violations = []
    
    # 检查 references/troubleshooting.md
    troubleshooting = skill_dir / "references" / "troubleshooting.md"
    if not troubleshooting.exists():
        return violations
    
    content = troubleshooting.read_text(encoding="utf-8")
    lines = content.split("\n")
    
    for i, line in enumerate(lines, 1):
        if line.startswith("|") and "error" in line.lower():
            # 计算列数
            cols = len([c for c in line.split("|") if c.strip()])
            if cols > 3:
                violations.append(TEViolation("TE-3", str(troubleshooting.relative_to(skill_dir.parent)), i,
                                             f"错误表列数过多 ({cols} 列)，应 ≤3 列"))
    
    return violations


def check_te4_json_paths(skill_dir: Path) -> List[TEViolation]:
    """TE-4: JSON paths 集中声明 — 检测重复的 JSON path 定义"""
    violations = []
    skill_md = skill_dir / "SKILL.md"
    
    if not skill_md.exists():
        return violations
    
    content = skill_md.read_text(encoding="utf-8")
    
    # 查找 JSON path 模式
    # 1. 匹配 $.properties.state 格式（标准 JSONPath）
    json_path_pattern = r"\$\.[a-zA-Z0-9_.\[\]]+"
    json_matches = re.findall(json_path_pattern, content)
    
    # 2. 匹配 Azure CLI --query 参数中的 JMESPath（无 $. 前缀）
    # 例如：--query "properties.provisioningState" 或 --query 'name'
    query_pattern = r'--query\s+["\']([^"\']+)["\']'
    query_matches = re.findall(query_pattern, content)
    
    # 合并所有路径
    all_paths = json_matches + query_matches
    
    # 统计每个 path 出现次数
    path_counts = {}
    for path in all_paths:
        path_counts[path] = path_counts.get(path, 0) + 1
    
    # 如果同一个 path 出现 >3 次，可能应该集中声明
    for path, count in path_counts.items():
        if count > 3:
            violations.append(TEViolation("TE-4", str(skill_md.relative_to(skill_dir.parent)), 0,
                                         f"JSON path '{path}' 重复 {count} 次，应集中声明", fixable=True))
    
    return violations


def check_te5_yaml_anchors(skill_dir: Path) -> List[TEViolation]:
    """TE-5: YAML anchors — 检测 example-config.yaml 中的重复配置"""
    violations = []
    example_config = skill_dir / "assets" / "example-config.yaml"
    
    if not example_config.exists():
        return violations
    
    content = example_config.read_text(encoding="utf-8")
    lines = content.split("\n")
    
    # 检测重复的配置块（简单启发式：相同的 key: value 对）
    seen = {}
    for i, line in enumerate(lines, 1):
        if ":" in line and not line.strip().startswith("#"):
            key_value = line.strip()
            if key_value in seen:
                violations.append(TEViolation("TE-5", str(example_config.relative_to(skill_dir.parent)), i,
                                             f"重复配置 '{key_value}'，应使用 YAML anchor", fixable=True))
            else:
                seen[key_value] = i
    
    return violations


def check_te6_cross_file_dup(skill_dir: Path) -> List[TEViolation]:
    """TE-6: 消除跨文件重复 — 检测 SKILL.md 与 references/ 的内容重复"""
    violations = []
    skill_md = skill_dir / "SKILL.md"
    references_dir = skill_dir / "references"
    
    if not skill_md.exists() or not references_dir.exists():
        return violations
    
    skill_content = skill_md.read_text(encoding="utf-8")
    skill_lines = set(skill_content.split("\n"))
    
    # 检查 references/ 中的文件
    for ref_file in references_dir.glob("*.md"):
        ref_content = ref_file.read_text(encoding="utf-8")
        ref_lines = set(ref_content.split("\n"))
        
        # 查找重复的非空行（排除标题和空行）
        common = skill_lines & ref_lines
        common = {line for line in common if line.strip() and not line.startswith("#")}
        
        if len(common) > 5:  # 超过 5 行重复
            violations.append(TEViolation("TE-6", str(ref_file.relative_to(skill_dir.parent)), 0,
                                         f"与 SKILL.md 有 {len(common)} 行重复内容"))
    
    return violations


def check_te7_content分层(skill_dir: Path) -> List[TEViolation]:
    """TE-7: 专业内容分层 — 检测 SKILL.md 中的深度内容"""
    violations = []
    skill_md = skill_dir / "SKILL.md"
    
    if not skill_md.exists():
        return violations
    
    content = skill_md.read_text(encoding="utf-8")
    
    # 检测应该在 references/ 中的深度内容
    depth_keywords = [
        r"##\s+AIOps",
        r"##\s+FinOps",
        r"##\s+深度分析",
        r"##\s+高级.*分析",
    ]
    
    for pattern in depth_keywords:
        if re.search(pattern, content, re.IGNORECASE):
            violations.append(TEViolation("TE-7", str(skill_md.relative_to(skill_dir.parent)), 0,
                                         f"SKILL.md 包含深度内容 '{pattern}'，应移至 references/"))
    
    return violations


def check_skill(skill_dir: Path) -> List[TEViolation]:
    """对单个 skill 执行完整 TE 检查"""
    all_violations = []
    
    all_violations.extend(check_te1_static_tables(skill_dir))
    all_violations.extend(check_te2_docstrings(skill_dir))
    all_violations.extend(check_te3_error_tables(skill_dir))
    all_violations.extend(check_te4_json_paths(skill_dir))
    all_violations.extend(check_te5_yaml_anchors(skill_dir))
    all_violations.extend(check_te6_cross_file_dup(skill_dir))
    all_violations.extend(check_te7_content分层(skill_dir))
    
    return all_violations


def main():
    parser = argparse.ArgumentParser(description="TE (Token Efficiency) 检查器")
    parser.add_argument("skill", nargs="?", help="要检查的 skill 目录 (如 azure-vm-ops)")
    parser.add_argument("--root", type=Path, default=Path(__file__).parent.parent, help="仓库根目录")
    args = parser.parse_args()
    
    # 确定要检查的 skills
    if args.skill:
        skill_dirs = [args.root / args.skill]
    else:
        skill_dirs = sorted(args.root.glob("azure-*-ops"))
    
    total_violations = 0
    fixable_count = 0
    
    for skill_dir in skill_dirs:
        if not skill_dir.is_dir():
            continue
        
        violations = check_skill(skill_dir)
        
        if violations:
            print(f"\n{skill_dir.name}:")
            for v in violations:
                print(f"  {v}")
                total_violations += 1
                if v.fixable:
                    fixable_count += 1
    
    print(f"\n{'='*60}")
    print(f"总计: {total_violations} 个违规 ({fixable_count} 个可自动修复)")
    
    if total_violations == 0:
        print("✓ 所有 skills 通过 TE 检查")
        return 0
    else:
        print("✗ 存在 TE 违规，需要修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())
