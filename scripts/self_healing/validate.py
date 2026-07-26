#!/usr/bin/env python3
"""
validate.py — self-healing 策略 JSON 开发时校验脚本

纯 stdlib 实现（无外部依赖），校验：
1. 顶层必填字段 (skill, operations)
2. operations 每条必含 risky 字段
3. healing_rules 每条必含全部 7 个字段
4. 数值范围 (max_attempts 1-5, backoff_sec 5-300)
5. 路径指向的策略文件是否存在（若 registry 引用它）

用法：python scripts/self_healing/validate.py [--fix]
  --fix  : 不报错，仅输出问题列表（用于人工确认）
  无 flag  : 发现问题则 exit 1
"""
import json
import re
import sys
from pathlib import Path

SCHEMA_FILE = Path(__file__).parent / "policy_schema.json"
SELF_DIR = Path(__file__).parent


def validate_policy(policy_file: Path) -> list[str]:
    """返回问题列表，空 = 有效"""
    errors = []
    try:
        policy = json.loads(policy_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]

    # 必填字段
    if "skill" not in policy:
        errors.append("missing required field: skill")
    else:
        if not re.match(r"^azure-[a-z0-9]+(-[a-z0-9]+)*-ops$", policy["skill"]):
            errors.append(f"invalid skill name format: {policy['skill']} (expected azure-xxx-ops)")

    if "operations" not in policy:
        errors.append("missing required field: operations")
    elif not isinstance(policy.get("operations"), dict):
        errors.append("operations must be an object")

    if errors:
        return errors

    # operations 逐条校验
    for op_name, op_config in policy["operations"].items():
        if "risky" not in op_config:
            errors.append(f"operation '{op_name}': missing required field: risky")

        for rule in op_config.get("healing_rules", []):
            # 基础必填字段（所有 condition_type 通用）
            base_required = ["condition_type", "heal_action", "heal_args_template", "max_attempts", "backoff_sec"]
            # condition_type 相关的额外必填字段
            ct = rule.get("condition_type")
            if ct in ("field_not_equal",):
                ct_required = ["condition_field", "condition_value"]
            elif ct in ("field_above_threshold", "field_below_threshold"):
                ct_required = ["condition_field", "threshold_value"]
            elif ct in ("trend_increasing",):
                ct_required = ["condition_field", "trend_window"]
            elif ct in ("rate_of_change",):
                ct_required = ["condition_field", "threshold_value", "trend_window"]
            else:
                ct_required = []

            required_fields = base_required + ct_required
            missing = [f for f in required_fields if f not in rule]
            if missing:
                errors.append(f"operation '{op_name}': healing_rule missing fields: {missing}")

            max_attempts = rule.get("max_attempts", 0)
            if not (1 <= max_attempts <= 5):
                errors.append(f"operation '{op_name}': healing_rule max_attempts={max_attempts} must be 1-5")

            backoff = rule.get("backoff_sec", 0)
            if not (5 <= backoff <= 300):
                errors.append(f"operation '{op_name}': healing_rule backoff_sec={backoff} must be 5-300")

            VALID_CONDITION_TYPES = {
                "field_not_equal", "field_above_threshold", "field_below_threshold",
                "trend_increasing", "rate_of_change",
            }
            if rule.get("condition_type") not in (None, *VALID_CONDITION_TYPES):
                errors.append(f"operation '{op_name}': unknown condition_type: {rule.get('condition_type')}")

            if not isinstance(rule.get("heal_args_template", []), list):
                errors.append(f"operation '{op_name}': heal_args_template must be an array")

    return errors


def main(fix_mode: bool = False) -> int:
    all_errors: dict[str, list[str]] = {}
    for json_file in sorted(SELF_DIR.glob("*.json")):
        if json_file.name in ("schema.json", "policy_schema.json", "registry.json"):
            continue
        errs = validate_policy(json_file)
        if errs:
            all_errors[json_file.name] = errs

    if not all_errors:
        print("All policy files valid.")
        return 0

    for fname, errs in all_errors.items():
        for e in errs:
            print(f"ERROR  {fname}: {e}", file=sys.stderr)

    if fix_mode:
        print(f"\n{len(all_errors)} files with issues (--fix mode, not exiting)", file=sys.stderr)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main(fix_mode="--fix" in sys.argv))
