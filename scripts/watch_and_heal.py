#!/usr/bin/env python3
"""Proactive watch → heal entry (MS L400 governance bridge).

Polls Azure Monitor metric alerts (or a local alert JSON dump) and maps
matched skills to auto_feedback_loop / escalate. Does NOT auto-run R2.

Usage::

    # Plan only (default)
    python3 scripts/watch_and_heal.py --alerts-file scripts/sample_alerts.json

    # Execute non-R2 observe path (requires AZURE_RESOURCE_GROUP)
    python3 scripts/watch_and_heal.py --alerts-file scripts/sample_alerts.json --execute

    # Live: list metric alerts via az
    python3 scripts/watch_and_heal.py --live --resource-group "$AZURE_RESOURCE_GROUP"
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from risk_tiers import apply_tier_gates

REPO_ROOT = Path(__file__).resolve().parent.parent

# Destructive symptom patterns first so R2 escalate path is reachable
SYMPTOM_MAP = [
    {"match": "vm_delete", "skill": "azure-vm-ops", "operation": "vm_delete"},
    {"match": "delete vm", "skill": "azure-vm-ops", "operation": "vm_delete"},
    {"match": "aks_delete", "skill": "azure-aks-ops", "operation": "aks_delete"},
    {"match": "vm", "skill": "azure-vm-ops", "operation": "vm_show"},
    {"match": "aks", "skill": "azure-aks-ops", "operation": "aks_list"},
    {"match": "storage", "skill": "azure-blobstorage-ops", "operation": "account_list"},
    {"match": "application-gateway", "skill": "azure-appgateway-ops", "operation": "ag_list"},
    {"match": "loadbalancer", "skill": "azure-loadbalancer-ops", "operation": "lb_list"},
    {"match": "frontdoor", "skill": "azure-frontdoor-ops", "operation": "afd_list"},
    {"match": "keyvault", "skill": "azure-keyvault-ops", "operation": "kv_list"},
    {"match": "vnet", "skill": "azure-vnet-ops", "operation": "vnet_list"},
]

# Read-only observe commands for --execute on R0/R1
_EXECUTE_CMDS = {
    ("azure-vm-ops", "vm_show"): "az vm list --resource-group {rg} --output json",
    ("azure-aks-ops", "aks_list"): "az aks list --resource-group {rg} --output json",
    ("azure-blobstorage-ops", "account_list"): "az storage account list --resource-group {rg} --output json",
    ("azure-appgateway-ops", "ag_list"): "az network application-gateway list --resource-group {rg} --output json",
    ("azure-loadbalancer-ops", "lb_list"): "az network lb list --resource-group {rg} --output json",
    ("azure-frontdoor-ops", "afd_list"): "az afd profile list --resource-group {rg} --output json",
    ("azure-keyvault-ops", "kv_list"): "az keyvault list --resource-group {rg} --output json",
    ("azure-vnet-ops", "vnet_list"): "az network vnet list --resource-group {rg} --output json",
}


def _map_alert(alert: dict[str, Any]) -> dict[str, Any] | None:
    text = json.dumps(alert).lower()
    for rule in SYMPTOM_MAP:
        if rule["match"] in text:
            return {"skill": rule["skill"], "operation": rule["operation"], "alert": alert}
    return None


def _fetch_live_alerts(resource_group: str) -> list[dict]:
    """Fetch metric alerts via az (read-only)."""
    cmd = [
        "az", "monitor", "metrics", "alert", "list",
        "--resource-group", resource_group,
        "--output", "json",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"[WARN] live alert fetch failed: {exc}", file=sys.stderr)
        return []
    if r.returncode != 0:
        print(f"[WARN] az failed: {r.stderr.strip()[:200]}", file=sys.stderr)
        return []
    try:
        data = json.loads(r.stdout)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def process_alerts(
    alerts: list[dict],
    *,
    dry_run: bool,
    resource_group: str = "",
) -> list[dict]:
    actions: list[dict] = []
    for alert in alerts:
        mapped = _map_alert(alert)
        if not mapped:
            actions.append({"status": "unmapped", "alert_name": alert.get("name", "?")})
            continue
        skill, operation = mapped["skill"], mapped["operation"]
        gates = apply_tier_gates(skill, operation)
        entry: dict[str, Any] = {
            "skill": skill,
            "operation": operation,
            "tier": gates["tier"],
            "alert_name": alert.get("name", alert.get("id", "?")),
            "action": "escalate" if gates["force_risky"] else "observe_heal",
            "dry_run": dry_run,
        }
        if gates["force_risky"]:
            entry["status"] = "planned_escalate" if dry_run else "escalated_r2"
            actions.append(entry)
            continue
        if dry_run:
            entry["status"] = "planned"
            entry["hint"] = (
                f"python scripts/auto_feedback_loop.py --skill {skill} "
                f"--operation {operation} --dry-run ..."
            )
            actions.append(entry)
            continue

        # --execute: call feedback loop for mapped read-only observe
        cmd_tmpl = _EXECUTE_CMDS.get((skill, operation))
        if not cmd_tmpl:
            entry["status"] = "blocked_no_command"
            actions.append(entry)
            continue
        if not resource_group:
            entry["status"] = "blocked_no_rg"
            actions.append(entry)
            continue
        from auto_feedback_loop import run_with_feedback

        cmd = cmd_tmpl.format(rg=resource_group)
        fb = run_with_feedback(
            skill=skill,
            operation=operation,
            command=cmd,
            desired_state={},
            dry_run=False,
            max_heal_attempts=0,  # observe-only for watch path
        )
        entry["status"] = f"executed_{fb.status}"
        entry["trace_id"] = fb.trace_id
        entry["message"] = fb.message
        actions.append(entry)
    return actions


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch alerts and plan/execute heal actions")
    parser.add_argument("--alerts-file", type=Path, help="JSON list of alerts")
    parser.add_argument("--live", action="store_true", help="Fetch via az monitor")
    parser.add_argument("--resource-group", default=os.environ.get("AZURE_RESOURCE_GROUP", ""))
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run non-R2 observe via auto_feedback_loop (default is plan-only)",
    )
    args = parser.parse_args()
    dry_run = not args.execute

    alerts: list[dict] = []
    if args.alerts_file:
        alerts = json.loads(args.alerts_file.read_text(encoding="utf-8"))
        if not isinstance(alerts, list):
            print("alerts-file must be a JSON list", file=sys.stderr)
            sys.exit(1)
    elif args.live:
        if not args.resource_group:
            print("Need --resource-group or AZURE_RESOURCE_GROUP", file=sys.stderr)
            sys.exit(1)
        alerts = _fetch_live_alerts(args.resource_group)
    else:
        print("Provide --alerts-file or --live", file=sys.stderr)
        sys.exit(1)

    actions = process_alerts(
        alerts, dry_run=dry_run, resource_group=args.resource_group,
    )
    out = {
        "time": datetime.now(timezone.utc).isoformat(),
        "alert_count": len(alerts),
        "plan_only": dry_run,
        "actions": actions,
    }
    out_dir = REPO_ROOT / "audit-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "watch-and-heal-last.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
