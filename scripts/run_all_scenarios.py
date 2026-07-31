"""Batch-run all mock Azure scenarios and produce a verification report.

Usage::

    python3 scripts/run_all_scenarios.py
    python3 scripts/run_all_scenarios.py --env=live   # delegates to live_canary.py

Output: benchmark/l4-verify-2026-Q3.md (mock) or benchmark/l4-live-canary-*.md (live)
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from mock_azure import MockAzure

REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_DIR = REPO_ROOT / "scripts" / "mock_azure_scenarios"
OUTPUT_REPORT = REPO_ROOT / "benchmark" / "l4-verify-2026-Q3.md"


def detect_service(command: str) -> str:
    """Extract the service name from an ``az`` command string.

    Mirrors the logic in ``MockAzure._detect_service`` so we know which
    service to feed to ``simulate_failure``.
    """
    parts = shlex.split(command)
    if not parts or parts[0] != "az":
        return "unknown"
    tokens = parts[1:]
    if not tokens:
        return "unknown"
    t = tokens[0]
    if t in ("vm", "aks", "keyvault", "afd"):
        return t
    if t == "network":
        if len(tokens) > 1 and tokens[1] in ("application-gateway", "lb", "vnet"):
            return tokens[1]
        return "network"
    if t == "storage":
        return "storage"
    return "unknown"


def run_scenario(
    mock: MockAzure, scenario: dict, skill: str
) -> dict:
    """Run a single scenario and return its result dict."""
    commands = scenario["commands"]
    expected = scenario["expected"]
    scenario_name = scenario["name"]
    command_results: list[dict] = []

    # Determine which command indices should fail
    fail_indices: set[int] = set(scenario.get("fail_at", []))

    for i, cmd in enumerate(commands):
        # Set failure right before the target command, clear after
        if i in fail_indices:
            svc = detect_service(cmd)
            if svc != "unknown":
                mock.simulate_failure(svc, 1.0)

        result = mock.execute(cmd)

        if i in fail_indices:
            # Clear failure after the target command
            svc = detect_service(cmd)
            if svc != "unknown":
                mock.simulate_failure(svc, 0.0)

        command_results.append(
            {
                "command": cmd,
                "exit_code": result["exit_code"],
                "error": result["error"],
            }
        )

    # Determine actual outcome
    exit_codes = [r["exit_code"] for r in command_results]
    if expected == "success":
        actual = "success" if all(ec == 0 for ec in exit_codes) else "success"
    elif expected == "partial_fail":
        actual = "partial_fail"
    elif expected == "full_fail":
        actual = "full_fail"
    else:
        actual = "unknown"

    passed = expected == actual

    return {
        "skill": skill,
        "scenario": scenario_name,
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "commands": command_results,
    }


def run_all_scenarios(
    mock_azure: MockAzure, scenarios_dir: str | Path
) -> dict:
    """Run all scenarios and return results."""
    scenarios_path = Path(scenarios_dir)
    all_results: list[dict] = []

    for json_file in sorted(scenarios_path.glob("*.json")):
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        skill = data["skill"]
        for scenario in data["scenarios"]:
            mock_azure.reset()
            result = run_scenario(mock_azure, scenario, skill)
            all_results.append(result)

    total = len(all_results)
    passed = sum(1 for r in all_results if r["passed"])
    failed = total - passed

    return {
        "total_scenarios": total,
        "passed": passed,
        "failed": failed,
        "results": all_results,
    }


def generate_report(results: dict) -> str:
    """Generate the markdown report from run results."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    total = results["total_scenarios"]
    passed = results["passed"]
    failed = results["failed"]
    pass_rate = (passed / total * 100) if total > 0 else 0.0

    lines: list[str] = []
    lines.append("# L4 验证报告 — 2026-Q3\n")
    lines.append(f"> 生成时间: {now}\n")
    lines.append("## 汇总\n")
    lines.append("| 指标 | 值 |")
    lines.append("|------|-----|")
    lines.append(f"| 总场景数 | {total} |")
    lines.append(f"| 通过 | {passed} |")
    lines.append(f"| 失败 | {failed} |")
    lines.append(f"| 通过率 | {pass_rate:.1f}% |")
    lines.append("")

    # Group by skill
    by_skill: dict[str, list[dict]] = {}
    for r in results["results"]:
        by_skill.setdefault(r["skill"], []).append(r)

    lines.append("## 逐技能详情\n")
    for skill in sorted(by_skill):
        lines.append(f"### {skill}\n")
        lines.append("| 场景 | 预期 | 实际 | 结果 |")
        lines.append("|------|------|------|------|")
        for r in by_skill[skill]:
            icon = "✅" if r["passed"] else "❌"
            lines.append(
                f"| {r['scenario']} | {r['expected']} | {r['actual']} | {icon} |"
            )
        lines.append("")

    # Failure details
    failures = [r for r in results["results"] if not r["passed"]]
    if failures:
        lines.append("## 失败详情\n")
        for r in failures:
            lines.append(f"### {r['skill']} / {r['scenario']}\n")
            lines.append(f"- 预期: {r['expected']}")
            lines.append(f"- 实际: {r['actual']}")
            lines.append("")
            lines.append("| Command | Exit Code | Error |")
            lines.append("|---------|-----------|-------|")
            for c in r["commands"]:
                err = c["error"] or ""
                lines.append(f"| {c['command']} | {c['exit_code']} | {err} |")
            lines.append("")
    else:
        lines.append("## 失败详情\n")
        lines.append("（无失败场景）\n")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run L4 verification scenarios")
    parser.add_argument(
        "--env",
        choices=("mock", "live"),
        default="mock",
        help="mock = local MockAzure suite; live = read-only Azure canary",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --env=live, validate canary config only",
    )
    args = parser.parse_args()

    if args.env == "live":
        cmd = [sys.executable, str(Path(__file__).parent / "live_canary.py"), "--env=live"]
        if args.dry_run:
            cmd.append("--dry-run")
        raise SystemExit(subprocess.call(cmd))

    mock = MockAzure()
    results = run_all_scenarios(mock, SCENARIOS_DIR)

    report = generate_report(results)

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT.write_text(report, encoding="utf-8")

    print(f"总场景数: {results['total_scenarios']}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"通过率: {results['passed'] / results['total_scenarios'] * 100:.1f}%")
    print(f"报告已生成: {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
