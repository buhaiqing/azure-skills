#!/usr/bin/env python3
"""C-7: 新 skill 8 步检查清单 — 自动化验证新 skill 是否符合规范

8 步检查：
1. Triggers: SHOULD/SHOULD-NOT 定义完整
2. Size: SKILL.md 行数在 100-150 范围（允许偏差）
3. Credentials: 使用 {{env.*}} 占位符，无硬编码密钥
4. Destructive: 删除/停止操作有安全门
5. Flow: 包含 Pre-flight/Execute/Validate/Recover 流程
6. Dual-path: 同时包含 CLI 和 SDK 路径
7. CADL: 包含复利资产沉淀触发行
8. References: 引用文件存在

用法:
    python scripts/skill_checklist.py azure-vm-ops
    python scripts/skill_checklist.py  # 检查所有 skills
"""
import argparse
import re
import sys
from pathlib import Path
from typing import List


class ChecklistViolation:
    def __init__(self, step: int, message: str, fixable: bool = False):
        self.step = step
        self.message = message
        self.fixable = fixable

    def __str__(self):
        fixable_mark = " [FIXABLE]" if self.fixable else ""
        return f"Step {self.step}{fixable_mark}: {self.message}"


def check_step1_triggers(skill_dir: Path) -> List[ChecklistViolation]:
    """Step 1: Triggers — SHOULD/SHOULD-NOT 定义完整"""
    violations = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        violations.append(ChecklistViolation(1, "SKILL.md not found"))
        return violations

    content = skill_md.read_text(encoding="utf-8")

    if "SHOULD Use When" not in content and "SHOULD use when" not in content.lower():
        violations.append(ChecklistViolation(1, "Missing 'SHOULD Use When' section"))

    if "SHOULD NOT Use When" not in content and "should not use when" not in content.lower():
        violations.append(ChecklistViolation(1, "Missing 'SHOULD NOT Use When' section"))

    return violations


def check_step2_size(skill_dir: Path) -> List[ChecklistViolation]:
    """Step 2: Size — SKILL.md 行数在合理范围 (80-180，目标 100-150)"""
    violations = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return violations

    line_count = len(skill_md.read_text(encoding="utf-8").splitlines())

    if line_count > 180:
        violations.append(ChecklistViolation(
            2, f"SKILL.md too long ({line_count} lines), target 100-150, max 180"))
    elif line_count < 80:
        violations.append(ChecklistViolation(
            2, f"SKILL.md too short ({line_count} lines), target 100-150, min 80"))

    return violations


def check_step3_credentials(skill_dir: Path) -> List[ChecklistViolation]:
    """Step 3: Credentials — 使用 {{env.*}} 占位符，无硬编码密钥"""
    violations = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return violations

    content = skill_md.read_text(encoding="utf-8")

    # 检测硬编码的 UUID 格式（可能是 subscription ID）
    uuid_pattern = r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b'
    if re.search(uuid_pattern, content, re.IGNORECASE):
        violations.append(ChecklistViolation(
            3, "Possible hardcoded UUID/subscription ID found, use {{env.AZURE_SUBSCRIPTION_ID}}"))

    # 检测要求用户粘贴密钥的指令
    paste_patterns = [
        r'paste\s+your\s+\w*secret',
        r'paste\s+your\s+\w*key',
        r'paste\s+your\s+\w*password',
        r'enter\s+your\s+\w*secret',
    ]
    for pattern in paste_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            violations.append(ChecklistViolation(
                3, f"Skill asks user to paste secret, use {{env.*}} placeholders instead"))
            break

    return violations


def check_step4_destructive(skill_dir: Path) -> List[ChecklistViolation]:
    """Step 4: Destructive — 删除/停止操作有安全门"""
    violations = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return violations

    content = skill_md.read_text(encoding="utf-8")

    # 检测是否包含破坏性操作
    destructive_keywords = [
        r'delete\b', r'deallocate\b', r'stop\b', r'terminate\b',
        r'purge\b', r'remove\b.*resource', r'destroy\b',
    ]

    has_destructive = False
    for pattern in destructive_keywords:
        if re.search(pattern, content, re.IGNORECASE):
            has_destructive = True
            break

    if not has_destructive:
        return violations  # No destructive ops, skip check

    # 检测安全门
    safety_patterns = [
        r'safety\s+gate',
        r'explicit\s+user\s+confirmation',
        r'must\s+obtain.*confirmation',
        r'require.*confirmation',
        r'human\s+confirmation',
        r'confirm.*deletion',
        r'confirm.*before',
    ]

    has_safety_gate = False
    for pattern in safety_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            has_safety_gate = True
            break

    if not has_safety_gate:
        violations.append(ChecklistViolation(
            4, "Destructive operations found but no safety gate documented"))

    return violations


def check_step5_flow(skill_dir: Path) -> List[ChecklistViolation]:
    """Step 5: Flow — 包含 Pre-flight/Execute/Validate/Recover 流程"""
    violations = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return violations

    content = skill_md.read_text(encoding="utf-8")

    required_keywords = [
        (r'pre[\-\s]?flight', "Pre-flight"),
        (r'execute', "Execute"),
        (r'validate', "Validate"),
        (r'recover', "Recover"),
    ]

    missing = []
    for pattern, name in required_keywords:
        if not re.search(pattern, content, re.IGNORECASE):
            missing.append(name)

    if missing:
        violations.append(ChecklistViolation(
            5, f"Missing execution flow keywords: {', '.join(missing)}"))

    return violations


def check_step6_dual_path(skill_dir: Path) -> List[ChecklistViolation]:
    """Step 6: Dual-path — 同时包含 CLI 和 SDK 路径"""
    violations = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return violations

    content = skill_md.read_text(encoding="utf-8")

    # 检测 CLI 路径
    cli_patterns = [
        r'azure\s+cli',
        r'az\s+\w+',
        r'cli\s*\(primary\)',
    ]
    has_cli = any(re.search(p, content, re.IGNORECASE) for p in cli_patterns)

    # 检测 SDK 路径
    sdk_patterns = [
        r'azure\s+sdk',
        r'from\s+azure\.mgmt',
        r'sdk\s*\(fallback\)',
        r'azure-identity',
    ]
    has_sdk = any(re.search(p, content, re.IGNORECASE) for p in sdk_patterns)

    if not has_cli:
        violations.append(ChecklistViolation(
            6, "Missing Azure CLI path (primary)"))
    if not has_sdk:
        violations.append(ChecklistViolation(
            6, "Missing Azure SDK path (fallback)"))

    return violations


def check_step7_cadl(skill_dir: Path) -> List[ChecklistViolation]:
    """Step 7: CADL — 包含复利资产沉淀触发行"""
    violations = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return violations

    content = skill_md.read_text(encoding="utf-8")

    # Must contain the Chinese phrase "复利资产沉淀机制" OR the full trigger phrase
    # Avoid matching bare "CADL" which could appear in unrelated contexts
    cadl_patterns = [
        r'复利资产沉淀机制',
        r'复盘并沉淀可复用资产',
    ]

    has_cadl = any(re.search(p, content) for p in cadl_patterns)

    if not has_cadl:
        violations.append(ChecklistViolation(
            7, "Missing CADL trigger line", fixable=True))

    return violations


def check_step8_references(skill_dir: Path) -> List[ChecklistViolation]:
    """Step 8: References — 引用文件存在"""
    violations = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return violations

    content = skill_md.read_text(encoding="utf-8")

    # 查找 Markdown 链接中的 references/ 路径
    ref_links = re.findall(r'\[.*?\]\((references/[^)]+)\)', content)

    for ref_path in ref_links:
        # Strip anchor (#anchor) and query (?query) parts
        file_path = ref_path.split('#')[0].split('?')[0]
        full_path = skill_dir / file_path
        if not full_path.exists():
            violations.append(ChecklistViolation(
                8, f"Referenced file not found: {ref_path}"))

    return violations


def check_skill_checklist(skill_dir: Path) -> List[ChecklistViolation]:
    """对单个 skill 执行完整 8 步检查"""
    all_violations = []

    all_violations.extend(check_step1_triggers(skill_dir))
    all_violations.extend(check_step2_size(skill_dir))
    all_violations.extend(check_step3_credentials(skill_dir))
    all_violations.extend(check_step4_destructive(skill_dir))
    all_violations.extend(check_step5_flow(skill_dir))
    all_violations.extend(check_step6_dual_path(skill_dir))
    all_violations.extend(check_step7_cadl(skill_dir))
    all_violations.extend(check_step8_references(skill_dir))

    return all_violations


def main():
    parser = argparse.ArgumentParser(description="新 skill 8 步检查清单")
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

        violations = check_skill_checklist(skill_dir)

        if violations:
            print(f"\n{skill_dir.name}:")
            for v in violations:
                print(f"  {v}")
                total_violations += 1
                if v.fixable:
                    fixable_count += 1
        else:
            print(f"{skill_dir.name}: ✓ All 8 steps passed")

    print(f"\n{'='*60}")
    print(f"总计: {total_violations} 个违规 ({fixable_count} 个可自动修复)")

    if total_violations == 0:
        print("✓ 所有 skills 通过 8 步检查")
        return 0
    else:
        print("✗ 存在违规，需要修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())
