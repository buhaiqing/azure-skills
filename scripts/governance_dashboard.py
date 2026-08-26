"""L4 Governance Dashboard — CLI dashboard for governance compliance.

Exposes governance合规可见性:
- Risk tier coverage (R0/R1/R2)
- Skill compliance (skills with live canary)
- Escalation audit (R2正确拒绝)
- Trace summary from audit-results/
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
RISK_TIERS_FILE = REPO_ROOT / "scripts" / "risk_tiers.json"
LIVE_CANARY_FILE = REPO_ROOT / "scripts" / "live_canary_scenarios.json"
AUDIT_RESULTS_DIR = REPO_ROOT / "audit-results"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _load_skill_dirs() -> list[Path]:
    """Return skill directories under REPO_ROOT."""
    if not REPO_ROOT.exists():
        return []
    return sorted(
        d for d in REPO_ROOT.iterdir()
        if d.is_dir() and d.name.startswith("azure-") and (d / "SKILL.md").exists()
    )


# ── Core data functions ───────────────────────────────────────────────────────


def governance_summary() -> dict[str, Any]:
    """汇总治理合规状态."""
    tiers_data = _load_json(RISK_TIERS_FILE)
    live_data = _load_json(LIVE_CANARY_FILE)
    skill_dirs = _load_skill_dirs()
    audit_files = list(AUDIT_RESULTS_DIR.glob("gcl-trace-*.json"))

    # skill compliance — union of filesystem skills and canary skills
    filesystem_skills = {d.name for d in skill_dirs}
    canary_skills_set = {s["skill"] for s in live_data.get("skills", [])}
    skill_set = filesystem_skills | canary_skills_set
    total_skills = len(skill_set)
    canary_skills = len(canary_skills_set & filesystem_skills)  # only skills with both filesystem + canary
    # audit results
    total_traces = len(audit_files)
    escalated = 0
    for f in audit_files:
        data = _load_json(f)
        spans = data.get("spans", [])
        for span in spans:
            meta = span.get("metadata", {})
            status = meta.get("status", "")
            if status in ("escalated", "human_confirm", "rejected"):
                escalated += 1
                break  # count once per trace

    # risk tier coverage
    tiers = tiers_data.get("tiers", {})
    tier_coverage: dict[str, dict[str, Any]] = {}
    for tier_id, tier_cfg in tiers.items():
        # count operations covered by canary per tier
        covered = sum(
            1 for s in live_data.get("skills", [])
            if s.get("tier") == tier_id
        )
        tier_coverage[tier_id] = {
            "covered": covered,
            "auto_heal": tier_cfg.get("auto_heal", False),
            "gcl_required": tier_cfg.get("gcl_required", False),
            "human_confirm": tier_cfg.get("human_confirm", False),
        }

    # governance status
    all_targets_met = (
        tier_coverage.get("R0", {}).get("covered", 0) > 0
        and tier_coverage.get("R1", {}).get("covered", 0) > 0
        and tier_coverage.get("R2", {}).get("covered", 0) > 0
    )
    governance_status = "compliant" if all_targets_met else "partial"

    return {
        "risk_tier_coverage": tier_coverage,
        "skill_compliance": {
            "total_skills": total_skills,
            "with_live_canary": canary_skills,
        },
        "trace_summary": {
            "total": total_traces,
            "escalated": escalated,
        },
        "governance_status": governance_status,
    }


def skill_compliance() -> dict[str, Any]:
    """Skill 级别合规状态."""
    live_data = _load_json(LIVE_CANARY_FILE)
    skill_dirs = _load_skill_dirs()
    skill_set = {d.name for d in skill_dirs}
    canary_map: dict[str, list[dict[str, Any]]] = {}
    for s in live_data.get("skills", []):
        canary_map.setdefault(s["skill"], []).append(s)

    rows = []
    for skill in sorted(skill_set):
        ops = canary_map.get(skill, [])
        rows.append({
            "skill": skill,
            "has_canary": len(ops) > 0,
            "canary_ops": len(ops),
            "tiers": sorted({op["tier"] for op in ops}),
        })
    return {"skills": rows, "total": len(rows), "with_canary": sum(1 for r in rows if r["has_canary"])}


def escalation_audit() -> dict[str, Any]:
    """Escalated 审计 — R2 正确拒绝验证."""
    audit_files = list(AUDIT_RESULTS_DIR.glob("gcl-trace-*.json"))
    rows = []
    for f in sorted(audit_files):
        data = _load_json(f)
        spans = data.get("spans", [])
        row = {
            "trace_id": data.get("id", f.stem),
            "skill": data.get("metadata", {}).get("skill", "unknown"),
            "status": data.get("gcl_status", "unknown"),
            "iterations": data.get("gcl_final_iter", 0),
            "escalated": False,
            "reason": "",
        }
        for span in spans:
            meta = span.get("metadata", {})
            status = meta.get("status", "")
            if status in ("escalated", "human_confirm", "rejected"):
                row["escalated"] = True
                row["reason"] = meta.get("message", status)
                break
        rows.append(row)

    escalated = [r for r in rows if r["escalated"]]
    return {
        "total": len(rows),
        "escalated": len(escalated),
        "clean": len(rows) - len(escalated),
        "traces": rows,
    }


def trace_summary() -> dict[str, Any]:
    """Trace 统计摘要."""
    audit_files = list(AUDIT_RESULTS_DIR.glob("gcl-trace-*.json"))
    statuses: dict[str, int] = {}
    tiers: dict[str, int] = {}
    for f in audit_files:
        data = _load_json(f)
        status = data.get("gcl_status", "unknown")
        statuses[status] = statuses.get(status, 0) + 1
        for span in data.get("spans", []):
            t = span.get("metadata", {}).get("tier", "unknown")
            tiers[t] = tiers.get(t, 0) + 1

    return {
        "total": len(audit_files),
        "statuses": statuses,
        "tiers": tiers,
    }


# ── CLI rendering ─────────────────────────────────────────────────────────────


def _render_header() -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         L4 GOVERNANCE DASHBOARD — Azure Skills          ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Generated : {now:<39} ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()


def _render_risk_tiers(data: dict[str, Any]) -> None:
    coverage = data.get("risk_tier_coverage", {})
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  Risk Tier Coverage                                     │")
    print("├────────┬─────────┬───────────┬─────────────────────────┤")
    print("│  Tier  │ Covered │ Auto-Heal │ GCL Required             │")
    print("├────────┼─────────┼───────────┼─────────────────────────┤")
    for tier in ("R0", "R1", "R2"):
        cfg = coverage.get(tier, {})
        covered = cfg.get("covered", 0)
        auto_heal = "✅" if cfg.get("auto_heal") else "❌"
        gcl = "✅" if cfg.get("gcl_required") else "—"
        print(f"│  {tier:<6} │  {covered:>5}  │  {auto_heal:<9} │  {gcl:<23} │")
    print("└────────┴─────────┴───────────┴─────────────────────────┘")
    print()


def _render_skill_compliance(data: dict[str, Any]) -> None:
    sc = data.get("skill_compliance", {})
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  Skill Compliance                                        │")
    print("├──────────────────────────────────────────────────────────┤")
    print(f"│  Total skills        : {sc.get('total_skills', 0):<36} │")
    print(f"│  With live canary    : {sc.get('with_live_canary', 0):<36} │")
    pct = (
        sc.get("with_live_canary", 0) / max(sc.get("total_skills", 1), 1) * 100
    )
    print(f"│  Coverage            : {pct:>5.1f}%{' '*31} │")
    print("└──────────────────────────────────────────────────────────┘")
    print()


def _render_trace_summary(summary_data: dict[str, Any]) -> None:
    ts = summary_data.get("trace_summary", {})
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  Trace Summary                                            │")
    print("├──────────────────────────────────────────────────────────┤")
    print(f"│  Total traces : {ts.get('total', 0):<40} │")
    print(f"│  Escalated   : {ts.get('escalated', 0):<40} │")
    status = summary_data.get("governance_status", "unknown")
    icon = "✅" if status == "compliant" else "⚠️"
    print(f"│  Status      : {icon} {status:<43} │")
    print("└──────────────────────────────────────────────────────────┘")
    print()


def _render_escalation_audit(data: dict[str, Any]) -> None:
    print("┌──────────────────────────────────────────────────────────┐")
    print("│  Escalation Audit                                         │")
    print("├──────────────────────────────────────────────────────────┤")
    print(f"│  Total traces : {data.get('total', 0):<40} │")
    print(f"│  Escalated    : {data.get('escalated', 0):<40} │")
    print(f"│  Clean        : {data.get('clean', 0):<40} │")
    print("└──────────────────────────────────────────────────────────┘")
    print()


def _render_table(summary_data: dict[str, Any], escalation_data: dict[str, Any]) -> None:
    _render_header()
    _render_risk_tiers(summary_data)
    _render_skill_compliance(summary_data)
    _render_trace_summary(summary_data)
    _render_escalation_audit(escalation_data)
    status = summary_data.get("governance_status", "unknown")
    if status == "compliant":
        print("✅ Governance status: COMPLIANT — all tiers covered")
    else:
        print("⚠️  Governance status: PARTIAL — some tiers uncovered")

def _render_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="L4 Governance Dashboard")
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="output format (default: table)",
    )
    args = parser.parse_args()

    summary_data = governance_summary()
    escalation_data = escalation_audit()

    # merge escalation count into summary for trace_summary
    summary_data["trace_summary"]["escalated"] = escalation_data["escalated"]

    if args.format == "json":
        full = {
            "governance_summary": summary_data,
            "skill_compliance": skill_compliance(),
            "escalation_audit": escalation_data,
            "trace_summary": trace_summary(),
        }
        _render_json(full)
    else:
        _render_table(summary_data, escalation_data)


if __name__ == "__main__":
    main()
