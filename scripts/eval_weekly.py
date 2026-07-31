#!/usr/bin/env python3
"""Weekly evaluation harness — metrics + optional LLM Critic sample.

Usage::

    python3 scripts/eval_weekly.py
    python3 scripts/eval_weekly.py --with-critic   # needs CRITIC_PROVIDER / API key

Writes: benchmark/eval-weekly-YYYYMMDD.md
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = REPO_ROOT / "benchmark"
SCRIPTS = Path(__file__).resolve().parent


def _run(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Weekly L4 / MS L400 evaluation")
    parser.add_argument("--with-critic", action="store_true")
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    lines = [
        "# Weekly Evaluation Report\n",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}\n",
    ]

    # 1) Mock suite
    code, out = _run([sys.executable, str(SCRIPTS / "run_all_scenarios.py")])
    lines.append("## Mock scenario suite\n")
    lines.append(f"Exit: {code}\n")
    lines.append("```")
    lines.append(out.strip()[:2000])
    lines.append("```\n")

    # 2) Metrics
    code2, out2 = _run([sys.executable, str(SCRIPTS / "metrics_collector.py")])
    lines.append("## Metrics collector\n")
    lines.append(f"Exit: {code2}\n")
    health = REPO_ROOT / "l4-health-report.json"
    if health.exists():
        data = json.loads(health.read_text(encoding="utf-8"))
        lines.append("```json")
        lines.append(json.dumps(data.get("l4_targets", data.get("metrics", {})), indent=2)[:1500])
        lines.append("```\n")
    else:
        lines.append(out2[:500] + "\n")

    # 3) Live canary dry-run (always CI-safe)
    code3, out3 = _run([sys.executable, str(SCRIPTS / "live_canary.py"), "--dry-run"])
    lines.append("## Live canary (dry-run)\n")
    lines.append(f"Exit: {code3}\n")
    lines.append("```")
    lines.append(out3.strip()[:1000])
    lines.append("```\n")

    # 4) Optional LLM critic smoke
    lines.append("## LLM Critic\n")
    if args.with_critic:
        critic = SCRIPTS / "llm_critic.py"
        if critic.exists():
            code4, out4 = _run([sys.executable, str(critic), "--help"])
            lines.append(f"llm_critic --help exit={code4}\n")
            lines.append(
                "> Full scoring requires `CRITIC_PROVIDER` + API key; "
                "fallback to rule-based Critic is documented in `manual/llm-critic.md`.\n"
            )
            if out4:
                lines.append("```")
                lines.append(out4.strip()[:800])
                lines.append("```\n")
        else:
            lines.append("llm_critic.py not found\n")
    else:
        lines.append(
            "Skipped (`--with-critic` not set). Fallback: `gcl_runner.py --critic rule`.\n"
        )

    BENCHMARK.mkdir(parents=True, exist_ok=True)
    path = BENCHMARK / f"eval-weekly-{stamp}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {path}")
    if code != 0 or code2 != 0 or code3 != 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
