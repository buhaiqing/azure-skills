#!/usr/bin/env python3
"""Live canary runner — MS L400 production evidence (read-only).

Usage::

    # Validate config without Azure (CI-safe)
    python3 scripts/live_canary.py --dry-run

    # Real subscription (requires az login + AZURE_RESOURCE_GROUP)
    python3 scripts/live_canary.py --env=live

Output: benchmark/l4-live-canary-YYYYMMDD.md (+ .json sidecar)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = Path(__file__).resolve().parent / "live_canary_scenarios.json"
BENCHMARK = REPO_ROOT / "benchmark"

_ENV_RE = re.compile(r"\{\{env\.(\w+)\}\}")


def _expand_to_argv(cmd_template: str, env: dict[str, str]) -> list[str]:
    """Expand {{env.X}} per-token so values never re-split into extra flags."""
    parts = shlex.split(cmd_template)
    out: list[str] = []
    for part in parts:
        def repl(m: re.Match[str]) -> str:
            key = m.group(1)
            if key not in env or not env[key]:
                raise ValueError(f"Missing env: {key}")
            val = env[key]
            if val.startswith("-"):
                raise ValueError(f"env {key} must not start with '-' (flag injection)")
            return val

        out.append(_ENV_RE.sub(repl, part))
    return out


def _run_az(argv: list[str], timeout: int = 60) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError:
        return -1, "", "az not found"


def _check_list(stdout: str) -> bool:
    try:
        data = json.loads(stdout)
        return isinstance(data, list)
    except json.JSONDecodeError:
        return False


def run_canary(*, dry_run: bool, env_mode: str) -> dict:
    data = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    skills = data["skills"]
    env = {
        "AZURE_RESOURCE_GROUP": os.environ.get("AZURE_RESOURCE_GROUP", ""),
        "AZURE_SUBSCRIPTION_ID": os.environ.get("AZURE_SUBSCRIPTION_ID", ""),
    }
    results: list[dict] = []
    mode = "dry_run" if dry_run or env_mode != "live" else "live"

    for item in skills:
        entry = {
            "skill": item["skill"],
            "operation": item["operation"],
            "tier": item.get("tier", "R0"),
            "command_template": item["command"],
            "status": "pending",
            "detail": "",
        }
        if mode == "dry_run":
            missing = [m.group(1) for m in _ENV_RE.finditer(item["command"])]
            entry["status"] = "dry_run_ok"
            entry["detail"] = f"requires env: {', '.join(sorted(set(missing)))}"
            results.append(entry)
            continue

        try:
            argv = _expand_to_argv(item["command"], env)
        except ValueError as exc:
            entry["status"] = "skipped"
            entry["detail"] = str(exc)
            results.append(entry)
            continue

        code, out, err = _run_az(argv)
        if code != 0:
            entry["status"] = "fail"
            entry["detail"] = (err or out)[:200]
        elif item.get("desired_check") == "is_list" and not _check_list(out):
            entry["status"] = "fail"
            entry["detail"] = "observe did not return JSON list"
        else:
            entry["status"] = "pass"
            entry["detail"] = "observe+diff ok (list)"
        results.append(entry)

    live_passed = sum(1 for r in results if r["status"] == "pass")
    contract_ok = sum(1 for r in results if r["status"] == "dry_run_ok")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    return {
        "mode": mode,
        "report_time": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "passed": live_passed if mode == "live" else contract_ok,
        "failed": failed,
        "skipped": skipped,
        "results": results,
    }


def _write_report(summary: dict) -> Path:
    BENCHMARK.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    md_path = BENCHMARK / f"l4-live-canary-{stamp}.md"
    json_path = BENCHMARK / f"l4-live-canary-{stamp}.json"

    lines = [
        "# L4 Live Canary Report\n",
        f"> Generated: {summary['report_time']}\n",
        f"> Mode: `{summary['mode']}`\n",
        "## Summary\n",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total | {summary['total']} |",
        f"| Passed | {summary['passed']} |",
        f"| Failed | {summary['failed']} |",
        f"| Skipped | {summary['skipped']} |",
        "",
        "## Per skill\n",
        "| Skill | Operation | Tier | Status | Detail |",
        "|-------|-----------|------|--------|--------|",
    ]
    for r in summary["results"]:
        lines.append(
            f"| {r['skill']} | {r['operation']} | {r['tier']} | {r['status']} | {r['detail']} |"
        )
    lines.append("")
    if summary["mode"] != "live":
        lines.append(
            "> Dry-run / non-live: set `AZURE_RESOURCE_GROUP` and run "
            "`python3 scripts/live_canary.py --env=live` for production evidence.\n"
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Live canary for MS L400")
    parser.add_argument("--env", choices=("mock", "live"), default="mock")
    parser.add_argument("--dry-run", action="store_true", help="Validate config only")
    args = parser.parse_args()

    dry = args.dry_run or args.env != "live"
    summary = run_canary(dry_run=dry, env_mode=args.env)
    path = _write_report(summary)
    print(f"mode={summary['mode']} total={summary['total']} "
          f"passed={summary['passed']} failed={summary['failed']} skipped={summary['skipped']}")
    print(f"report: {path}")
    if summary["failed"] > 0:
        sys.exit(1)
    # Live mode with zero passes (all skipped/missing env) is a false-positive success
    if summary["mode"] == "live" and summary["passed"] == 0:
        print("ERROR: live canary produced zero passes (check AZURE_RESOURCE_GROUP)", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
