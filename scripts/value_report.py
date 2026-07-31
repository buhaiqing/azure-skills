#!/usr/bin/env python3
"""Business value KPI report — MS L400 Business strategy pillar.

Usage::

    python3 scripts/value_report.py
    python3 scripts/value_report.py --hours-per-escalation 0.5

Reads: l4-health-report.json, audit-results/gcl-trace-*.json (optional)
Writes: benchmark/value-report-YYYYMM.md
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HEALTH = REPO_ROOT / "l4-health-report.json"
AUDIT = REPO_ROOT / "audit-results"
BENCHMARK = REPO_ROOT / "benchmark"

# Conservative default: each successful auto-heal avoids ~15 min of human toil
DEFAULT_HOURS_PER_HEAL = 0.25
DEFAULT_HOURS_PER_ESCALATION = 0.5


def _load_health() -> dict:
    if not HEALTH.exists():
        return {}
    return json.loads(HEALTH.read_text(encoding="utf-8"))


def _count_traces() -> dict[str, int]:
    counts = {"traces": 0, "healed_hint": 0, "escalated_hint": 0}
    if not AUDIT.is_dir():
        return counts
    for p in AUDIT.glob("gcl-trace-*.json"):
        counts["traces"] += 1
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        # Only count explicit heal / escalate statuses — never GCL PASS
        status = str(data.get("gcl_status", "")).lower()
        if status == "healed":
            counts["healed_hint"] += 1
        elif status in ("escalated", "safety_fail"):
            counts["escalated_hint"] += 1
    for p in AUDIT.glob("*.json"):
        if p.name.startswith("gcl-trace"):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        st = data.get("status")
        if st == "healed":
            counts["healed_hint"] += 1
        elif st == "escalated":
            counts["escalated_hint"] += 1
    return counts


def build_report(hours_heal: float, hours_esc: float) -> dict:
    health = _load_health()
    metrics = health.get("metrics", {})
    targets = health.get("l4_targets", {})
    traces = _count_traces()

    auto_heal_rate = targets.get("auto_heal_success_rate", {}).get("actual")
    if auto_heal_rate is None:
        auto_heal_rate = metrics.get("auto_heal_success_rate")
    esc_rate = targets.get("escalation_rate", {}).get("actual")
    if esc_rate is None:
        esc_rate = metrics.get("escalation_rate")
    total = health.get("total_scenarios", 0)

    # Strict: only explicit healed/escalated trace counts — no synthetic inflate
    heals = traces["healed_hint"]
    escalations = traces["escalated_hint"]
    data_sufficient = heals > 0 or escalations > 0 or traces["traces"] > 0

    hours_saved = heals * hours_heal if data_sufficient else None
    hours_escalation_cost = escalations * hours_esc if data_sufficient else None
    net = None
    if hours_saved is not None and hours_escalation_cost is not None:
        net = round(hours_saved - hours_escalation_cost, 2)

    return {
        "report_time": datetime.now(timezone.utc).isoformat(),
        "kpis": {
            "auto_heal_success_rate_pct": auto_heal_rate if auto_heal_rate is not None else "n/a",
            "escalation_rate_pct": esc_rate if esc_rate is not None else "n/a",
            "estimated_heal_events": heals if data_sufficient else "n/a",
            "estimated_escalations": escalations if data_sufficient else "n/a",
            "estimated_hours_saved": round(hours_saved, 2) if hours_saved is not None else "n/a",
            "estimated_escalation_hours": (
                round(hours_escalation_cost, 2) if hours_escalation_cost is not None else "n/a"
            ),
            "net_hours_benefit": net if net is not None else "n/a",
            "trace_files": traces["traces"],
            "scenarios_in_health_report": total,
        },
        "assumptions": {
            "hours_per_heal": hours_heal,
            "hours_per_escalation": hours_esc,
            "counting_rule": "only gcl_status/status == healed|escalated; never GCL PASS",
        },
    }


def write_markdown(report: dict) -> Path:
    BENCHMARK.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m")
    path = BENCHMARK / f"value-report-{stamp}.md"
    k = report["kpis"]
    a = report["assumptions"]
    lines = [
        "# Azure Skills — Value Report\n",
        f"> Generated: {report['report_time']}\n",
        "## Business KPIs (MS L400)\n",
        "| KPI | Value |",
        "|-----|-------|",
        f"| Auto-heal success rate | {k['auto_heal_success_rate_pct']} |",
        f"| Escalation rate | {k['escalation_rate_pct']} |",
        f"| Estimated heal events | {k['estimated_heal_events']} |",
        f"| Estimated escalations | {k['estimated_escalations']} |",
        f"| Estimated hours saved | {k['estimated_hours_saved']} |",
        f"| Escalation toil hours | {k['estimated_escalation_hours']} |",
        f"| Net hours benefit | {k['net_hours_benefit']} |",
        "",
        "## Assumptions\n",
        f"- Hours per successful heal: {a['hours_per_heal']}",
        f"- Hours per escalation: {a['hours_per_escalation']}",
        f"- Counting: {a.get('counting_rule', '')}",
        "",
        "> Cost anomaly interception: enable `--observe-cost` on "
        "`auto_feedback_loop.py` and review `cost_heal.json` hits in traces.\n",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    sidecar = path.with_suffix(".json")
    sidecar.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--hours-per-heal", type=float, default=DEFAULT_HOURS_PER_HEAL)
    p.add_argument("--hours-per-escalation", type=float, default=DEFAULT_HOURS_PER_ESCALATION)
    args = p.parse_args()
    report = build_report(args.hours_per_heal, args.hours_per_escalation)
    path = write_markdown(report)
    print(json.dumps(report["kpis"], indent=2))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
