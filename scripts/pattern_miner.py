#!/usr/bin/env python3
"""
pattern_miner.py — 异常模式知识库挖掘

扫描 .runtime/findings/ 目录，提取高频异常模式并归因。
输出给 CADL 机制用于沉淀为可复用资产。

用法：
  python scripts/pattern_miner.py [--min-frequency 3] [--days 30]
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

RUNTIME_DIR = Path(__file__).parent.parent / ".runtime"
FINDINGS_DIR = RUNTIME_DIR / "findings"
OUTPUT_DIR = RUNTIME_DIR / "patterns"


def scan_findings(days: int = 30) -> list[dict]:
    """扫描 .runtime/findings/ 中指定天数内的所有 finding 文件"""
    if not FINDINGS_DIR.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    findings = []
    for f in FINDINGS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            ts = data.get("date", "")
            if ts:
                dt = datetime.fromisoformat(ts)
                if dt >= cutoff:
                    findings.append(data)
        except (json.JSONDecodeError, ValueError):
            continue
    return findings


def mine_patterns(findings: list[dict], min_frequency: int = 3) -> dict[str, Any]:
    """从 findings 中提取高频模式"""
    if not findings:
        return {"patterns": [], "summary": "no findings to analyze"}

    # 按 (skill, operation, failure_type) 组合统计
    combo_counter: Counter = Counter()
    # 按 failure_type 统计
    type_counter: Counter = Counter()
    # 按 skill 统计
    skill_counter: Counter = Counter()

    for f in findings:
        key = (f.get("skill", "unknown"), f.get("operation", "unknown"),
               f.get("failure_type", "unknown"))
        combo_counter[key] += 1
        type_counter[f.get("failure_type", "unknown")] += 1
        skill_counter[f.get("skill", "unknown")] += 1

    # 提取高频组合模式
    patterns = []
    for (skill, operation, failure_type), count in combo_counter.most_common():
        if count >= min_frequency:
            patterns.append({
                "skill": skill,
                "operation": operation,
                "failure_type": failure_type,
                "frequency": count,
                "recommendation": _suggest_cadl_entry(skill, operation, failure_type),
            })

    return {
        "patterns": patterns,
        "summary": {
            "total_findings": len(findings),
            "unique_combinations": len(combo_counter),
            "top_failure_types": dict(type_counter.most_common(5)),
            "top_skills": dict(skill_counter.most_common(5)),
        },
    }


def _suggest_cadl_entry(skill: str, operation: str, failure_type: str) -> str:
    """根据高频模式推荐 CADL 沉淀内容"""
    suggestions = {
        "heal_exhausted": (
            f"Add healing strategy for {skill}/{operation} — "
            f"currently exhausted with no self-healing path"
        ),
        "observe_failed": (
            f"Check health_check configuration for {skill}/{operation} — "
            f"observation step failing repeatedly"
        ),
        "command_failed": (
            f"Review command syntax for {skill}/{operation} — "
            f"execution failing with non-zero exit code"
        ),
        "no_heal_policy": (
            f"Implement healing_rules for {skill}/{operation} — "
            f"state mismatch with no automatic remediation"
        ),
    }
    return suggestions.get(failure_type,
                           f"Review {skill}/{operation} for recurring {failure_type} pattern")


def write_patterns_to_memory(patterns: dict[str, Any], storage_dir: Path) -> int:
    """Write mined patterns to memory_store as failure records.

    Each pattern becomes a (skill, symptom, strategy) entry with success=False.
    This seeds the memory store with known failure modes so auto_feedback_loop
    can check if a current failure matches a known pattern.

    Returns number of patterns written.
    """
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=storage_dir)
    written = 0

    for pattern in patterns.get("patterns", []):
        skill = pattern["skill"]
        operation = pattern["operation"]
        failure_type = pattern["failure_type"]
        recommendation = pattern["recommendation"]

        # Symptom: operation + failure_type (e.g., "vm_create:heal_exhausted")
        symptom = f"{operation}:{failure_type}"

        # Strategy: the recommendation text (truncated to 100 chars for storage)
        strategy = recommendation[:100] if len(recommendation) > 100 else recommendation

        # Record as failure (success=False) — these are known failure patterns
        store.record(skill, symptom, strategy, success=False)
        written += 1

    return written


def write_patterns_report(patterns: dict[str, Any], output_dir: Path = OUTPUT_DIR):
    """将模式分析结果写入 .runtime/patterns/ 目录"""
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = output_dir / f"patterns-{today}.json"
    path.write_text(json.dumps(patterns, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description="异常模式知识库挖掘")
    parser.add_argument("--min-frequency", type=int, default=3,
                        help="最小频次阈值（默认 3）")
    parser.add_argument("--days", type=int, default=30,
                        help="扫描最近 N 天的 findings（默认 30）")
    args = parser.parse_args()

    findings = scan_findings(days=args.days)
    if not findings:
        print(f"ℹ️  No findings found in {FINDINGS_DIR} for the last {args.days} days.")
        sys.exit(0)

    patterns = mine_patterns(findings, min_frequency=args.min_frequency)
    path = write_patterns_report(patterns)

    # Write patterns to memory store for auto_feedback_loop integration
    memory_dir = Path(__file__).parent / "memory" / "data"
    written = write_patterns_to_memory(patterns, memory_dir)
    if written > 0:
        print(f"   📝  Wrote {written} patterns to memory store ({memory_dir})")

    summary = patterns["summary"]
    print(f"✅  Pattern mining complete — {path}")
    print(f"   Total findings: {summary['total_findings']}")
    print(f"   Unique (skill, op, failure) combos: {summary['unique_combinations']}")
    print(f"   Top failure types: {json.dumps(summary['top_failure_types'], ensure_ascii=False)}")
    print(f"   Top skills: {json.dumps(summary['top_skills'], ensure_ascii=False)}")

    if patterns["patterns"]:
        print(f"\n   📊  High-frequency patterns (≥{args.min_frequency} occurrences):")
        for p in patterns["patterns"]:
            print(f"       [{p['skill']}/{p['operation']}] {p['failure_type']} x{p['frequency']}")
            print(f"       → {p['recommendation']}")
    else:
        print(f"\n   No patterns above frequency threshold ({args.min_frequency}).")


if __name__ == "__main__":
    main()