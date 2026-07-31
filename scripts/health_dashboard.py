"""L4 Health Dashboard — CLI dashboard for skill-by-skill health and 7-day trend.

Usage::

    python3 scripts/health_dashboard.py [--report PATH] [--trend-dir PATH]

Output: formatted CLI dashboard (no external dependencies, stdlib only).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = REPO_ROOT / "l4-health-report.json"
DEFAULT_TREND_DIR = REPO_ROOT / "benchmark"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[WARN] Could not load {path}: {exc}", file=sys.stderr)
        return {}


def _send_to_azure_monitor(data: dict[str, Any], resource_id: str | None = None) -> bool:
    """Write L4 metrics to Azure Monitor via az CLI.

    Always writes ``audit-results/azure-monitor-payload.json`` for offline evidence.
    Live ingest requires AZURE_SUBSCRIPTION_ID + AZURE_APP_INSIGHTS_RESOURCE_ID (or --resource-id).
    """
    subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
    l4_targets = data.get("l4_targets", {})
    total = data.get("total_scenarios", 0)
    passed = data.get("passed", 0)
    failed = data.get("failed", 0)

    metrics = [
        ("l4_safety_pass_rate", l4_targets.get("safety_pass_rate", {}).get("actual", 0), "0-100"),
        ("l4_auto_heal_success_rate", l4_targets.get("auto_heal_success_rate", {}).get("actual", 0), "0-100"),
        ("l4_escalation_rate", l4_targets.get("escalation_rate", {}).get("actual", 0), "0-100"),
        ("l4_scenarios_total", total, ""),
        ("l4_scenarios_passed", passed, ""),
        ("l4_scenarios_failed", failed, ""),
    ]

    app_insights_id = resource_id or os.environ.get("AZURE_APP_INSIGHTS_RESOURCE_ID", "")

    payload_path = REPO_ROOT / "audit-results" / "azure-monitor-payload.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "resource_id": app_insights_id or None,
        "subscription_id": subscription_id or None,
        "metrics": {name: value for name, value, _ in metrics},
    }
    payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[INFO] Wrote Monitor payload: {payload_path}")

    if not subscription_id:
        print("[WARN] AZURE_SUBSCRIPTION_ID not set, skipping live Azure Monitor ingest", file=sys.stderr)
        return False
    if not app_insights_id:
        print("[WARN] AZURE_APP_INSIGHTS_RESOURCE_ID not set and no --resource-id provided, skipping live ingest", file=sys.stderr)
        return False

    cmd_base = [
        "az", "monitor", "app-insights", "metrics",
        "create",
        "--resource-id", app_insights_id,
        "--interval", "PT1M",
    ]

    success = True
    for metric_name, value, _description in metrics:
        cmd = cmd_base + [
            "--metric", metric_name,
            "--value", str(value),
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"[WARN] Failed to send metric {metric_name}: {result.stderr.strip()}", file=sys.stderr)
                success = False
        except Exception as exc:
            print(f"[WARN] Exception sending metric {metric_name}: {exc}", file=sys.stderr)
            success = False

    return success


def _load_trend_reports(trend_dir: Path, days: int = 7) -> list[dict[str, Any]]:
    """Load the N most-recent benchmark reports from trend_dir."""
    reports: list[dict[str, Any]] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    if not trend_dir.is_dir():
        return reports

    for path in sorted(trend_dir.glob("l4-verify-*.md")):
        # Try to find a matching JSON sidecar, or parse the md directly
        json_path = path.with_suffix(".json")
        if json_path.exists():
            data = _load_json(json_path)
            if data:
                reports.append(data)
        else:
            # Fallback: try to extract timestamp from filename
            # e.g. l4-verify-2026-Q3.md
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if mtime >= cutoff:
                data = _load_json(DEFAULT_REPORT)  # current only
                if data and data not in reports:
                    reports.append(data)

    # Deduplicate by report_time
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for r in reports:
        rt = r.get("report_time", "")
        if rt not in seen:
            seen.add(rt)
            unique.append(r)

    return unique


def _render_header(report_time: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║            L4 HEALTH DASHBOARD — Azure Skills            ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Report time: {report_time:<39} ║")
    print(f"║  Generated : {now:<39} ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()


def _render_l4_targets(data: dict[str, Any]) -> None:
    targets = data.get("l4_targets", {})
    metrics = data.get("metrics", {})

    print("┌──────────────────────────────────────────────────────────┐")
    print("│  L4 Certification Targets                                 │")
    print("├──────────────────────┬──────────┬──────────┬────────────┤")
    print("│  Metric              │  Target  │  Actual  │  Status    │")
    print("├──────────────────────┼──────────┼──────────┼────────────┤")

    rows = [
        ("Safety Pass Rate",      targets.get("safety_pass_rate", {}),      "≥100%"),
        ("Auto-Heal Success Rate", targets.get("auto_heal_success_rate", {}), "≥85%"),
        ("Escalation Rate",        targets.get("escalation_rate", {}),        "≤15%"),
    ]

    for label, tgt, threshold_str in rows:
        actual = tgt.get("actual", "—")
        met = tgt.get("met", False)
        status = "✅ PASS" if met else "❌ FAIL"
        print(f"│  {label:<19} │  {threshold_str:<8} │  {actual:>7}% │  {status:<8} │")

    avg_mttr = metrics.get("avg_mttr_ms", "—")
    print(f"│  Avg MTTR (ms)        │    —     │  {avg_mttr:>7} │  —          │")
    print("└──────────────────────┴──────────┴──────────┴────────────┘")
    print()


def _render_by_skill(data: dict[str, Any]) -> None:
    by_skill = data.get("by_skill", {})

    print("┌──────────────────────────────────────────────────────────┐")
    print("│  Skill-by-Skill Health                                    │")
    print("├─────────────────────────────────┬────────┬───────┬──────┤")
    print("│  Skill                          │  Pass  │  Fail │  %   │")
    print("├─────────────────────────────────┼────────┼───────┼──────┤")

    for skill in sorted(by_skill.keys()):
        stats = by_skill[skill]
        total = stats.get("total", 0)
        passed = stats.get("passed", 0)
        failed = stats.get("failed", 0)
        pct = (passed / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"│  {skill:<31} │  {passed:>6} │  {failed:>5} │  {pct:>5.1f}% │")
        print(f"│  {'':31} │  [{bar}]                  │")

    print("└─────────────────────────────────┴────────┴───────┴──────┘")
    print()


def _render_trend(reports: list[dict[str, Any]]) -> None:
    if not reports:
        print("┌──────────────────────────────────────────────────────────┐")
        print("│  7-Day Trend (no historical data yet)                     │")
        print("└──────────────────────────────────────────────────────────┘")
        print()
        return

    print("┌──────────────────────────────────────────────────────────┐")
    print("│  7-Day Trend                                             │")
    print("├──────────────────────┬──────────┬──────────┬────────────┤")
    print("│  Date                │  Pass %  │  Escal.  │  Auto-Heal │")
    print("├──────────────────────┼──────────┼──────────┼────────────┤")

    for r in reports[-7:]:
        rt = r.get("report_time", "—")[:10]
        metrics = r.get("metrics", {})
        safety = metrics.get("safety_pass_rate", 0)
        escal = metrics.get("escalation_rate", 0)
        auto_heal = metrics.get("auto_heal_success_rate", 0)
        print(f"│  {rt:<20} │  {safety:>7.1f}% │  {escal:>7.1f}% │  {auto_heal:>9.1f}% │")

    print("└──────────────────────┴──────────┴──────────┴────────────┘")
    print()


def _render_summary(data: dict[str, Any]) -> None:
    total = data.get("total_scenarios", 0)
    passed = data.get("passed", 0)
    failed = data.get("failed", 0)

    all_targets_met = all(
        t.get("met", False) for t in data.get("l4_targets", {}).values()
    )

    print("┌──────────────────────────────────────────────────────────┐")
    print("│  Summary                                                  │")
    print("├──────────────────────────────────────────────────────────┤")
    print(f"│  Total scenarios : {total:<36} │")
    print(f"│  Passed          : {passed:<36} │")
    print(f"│  Failed          : {failed:<36} │")
    print(f"│  L4 Certified    : {'✅ YES — all targets met' if all_targets_met else '❌ NO — targets not met':<25} │")
    print("└──────────────────────────────────────────────────────────┘")
    print()

    if all_targets_met:
        print("🎉 All L4 certification targets met. System is operating at L4.")
    else:
        print("⚠️  Some L4 targets not yet met. Review the details above.")


def main() -> None:
    parser = argparse.ArgumentParser(description="L4 Health Dashboard")
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Path to l4-health-report.json (default: {DEFAULT_REPORT})",
    )
    parser.add_argument(
        "--trend-dir",
        type=Path,
        default=DEFAULT_TREND_DIR,
        help=f"Directory containing historical benchmark reports (default: {DEFAULT_TREND_DIR})",
    )
    parser.add_argument(
        "--azure-monitor",
        action="store_true",
        help="Write L4 metrics to Azure Monitor (requires AZURE_SUBSCRIPTION_ID and AZURE_APP_INSIGHTS_RESOURCE_ID env vars, or --resource-id)",
    )
    parser.add_argument(
        "--resource-id",
        type=str,
        default=None,
        help="Azure resource ID for Application Insights (used with --azure-monitor)",
    )
    args = parser.parse_args()

    data = _load_json(args.report)
    if not data:
        print("[ERROR] No report data loaded. Run scripts/run_all_scenarios.py first.", file=sys.stderr)
        sys.exit(1)

    trend_reports = _load_trend_reports(args.trend_dir)

    if args.azure_monitor:
        _send_to_azure_monitor(data, args.resource_id)

    _render_header(data.get("report_time", "—"))
    _render_l4_targets(data)
    _render_by_skill(data)
    _render_trend(trend_reports)
    _render_summary(data)


if __name__ == "__main__":
    main()
