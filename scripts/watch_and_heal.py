#!/usr/bin/env python3
"""Proactive watch → heal entry (MS L400 governance bridge).

Polls Azure Monitor metric alerts (or a local alert JSON dump) and maps
matched skills to auto_feedback_loop / escalate. Does NOT auto-run R2.

Usage::

    # Plan only (default)
    python3 scripts/watch_and_heal.py --alerts-file scripts/sample_alerts.json

    # Execute non-R2 observe path (requires AZURE_RESOURCE_GROUP)
    python3 scripts/watch_and_heal.py --alerts-file scripts/sample_alerts.json --execute

    # Live: list metric alerts via az monitor
    python3 scripts/watch_and_heal.py --alert-source monitor --resource-group "$AZURE_RESOURCE_GROUP" --execute
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

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
    ("azure-vm-ops", "vm_restart"): "az vm restart --resource-group {rg} --ids $(az vm list -g {rg} --query '[0].id' -o tsv) --output json",
    ("azure-aks-ops", "aks_list"): "az aks list --resource-group {rg} --output json",
    ("azure-blobstorage-ops", "account_list"): "az storage account list --resource-group {rg} --output json",
    ("azure-appgateway-ops", "ag_list"): "az network application-gateway list --resource-group {rg} --output json",
    ("azure-appgateway-ops", "ag_restart"): "az network application-gateway restart --resource-group {rg} --name {name} --output json",
    ("azure-loadbalancer-ops", "lb_list"): "az network lb list --resource-group {rg} --output json",
    ("azure-frontdoor-ops", "afd_list"): "az afd profile list --resource-group {rg} --output json",
    ("azure-keyvault-ops", "kv_list"): "az keyvault list --resource-group {rg} --output json",
    ("azure-vnet-ops", "vnet_list"): "az network vnet list --resource-group {rg} --output json",
}

# Alert rules cache (loaded lazily)
_alert_rules: Optional[list[dict]] = None


def _load_alert_rules() -> list[dict]:
    """Load alert_rules.json from scripts/ directory."""
    global _alert_rules
    if _alert_rules is not None:
        return _alert_rules
    rules_path = Path(__file__).parent / "alert_rules.json"
    if rules_path.exists():
        try:
            data = json.loads(rules_path.read_text(encoding="utf-8"))
            _alert_rules = data.get("alert_rules", [])
        except (json.JSONDecodeError, OSError):
            _alert_rules = []
    else:
        _alert_rules = []
    return _alert_rules


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


def _fetch_monitor_alerts(resource_group: str) -> list[dict]:
    """Fetch metric alerts via az monitor metrics alert list (read-only).

    Returns a list of alert objects with alert_name, resource_type, and
    condition extracted for rule matching.
    """
    cmd = [
        "az", "monitor", "metrics", "alert", "list",
        "--resource-group", resource_group,
        "--output", "json",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"[WARN] monitor alert fetch failed: {exc}", file=sys.stderr)
        return []
    if r.returncode != 0:
        print(f"[WARN] az monitor metrics alert list failed: {r.stderr.strip()[:200]}", file=sys.stderr)
        return []
    try:
        data = json.loads(r.stdout)
        raw_alerts = data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []

    # Normalize to a flat alert dict with alert_name, resource_type, and condition
    normalized = []
    for alert in raw_alerts:
        name = (
            alert.get("name")
            or alert.get("properties", {}).get("alertName")
            or alert.get("id", "?")
        )
        resource_type = (
            alert.get("type")
            or alert.get("properties", {}).get("resourceType")
            or ""
        )
        condition = (
            alert.get("properties", {}).get("condition", {})
            or alert.get("condition", {})
        )
        normalized.append({
            "alert_name": name,
            "resource_type": resource_type,
            "condition": condition,
            "original": alert,
        })
    return normalized


def _alert_to_heal_action(alert: dict[str, Any], rules: list[dict]) -> Optional[tuple[str, str, str]]:
    """Match an alert against alert_rules.json and return (heal_skill, heal_operation, risk_tier).

    Returns None if no rule matches.
    R2 tier returns (skill, op, "R2") — caller must enforce human_confirm=True, auto_heal=False.
    """
    alert_name = alert.get("alert_name", "")
    resource_type = alert.get("resource_type", "")
    text_lower = f"{alert_name} {resource_type}".lower()

    for rule in rules:
        pattern = rule.get("alert_name_pattern", "")
        if re.search(pattern, alert_name, re.IGNORECASE) or re.search(pattern, text_lower, re.IGNORECASE):
            return (
                rule.get("heal_skill", ""),
                rule.get("heal_operation", ""),
                rule.get("risk_tier", "R1"),
            )
    return None


def process_alerts(
    alerts: list[dict],
    *,
    dry_run: bool,
    resource_group: str = "",
    use_alert_rules: bool = False,
) -> list[dict]:
    """Process alerts and return heal actions.

    Args:
        alerts: list of alert dicts (from _fetch_live_alerts or _fetch_monitor_alerts)
        dry_run: if True, only plan without executing
        resource_group: Azure resource group name
        use_alert_rules: if True, use alert_rules.json for mapping; otherwise use SYMPTOM_MAP
    """
    actions: list[dict] = []
    rules = _load_alert_rules() if use_alert_rules else []

    for alert in alerts:
        # Use alert_rules.json mapping if enabled and rules available
        heal_action: Optional[tuple[str, str, str]] = None
        if use_alert_rules and rules:
            heal_action = _alert_to_heal_action(alert, rules)

        # Fall back to SYMPTOM_MAP
        if not heal_action:
            mapped = _map_alert(alert.get("original", alert) if "original" in alert else alert)
            if not mapped:
                actions.append({"status": "unmapped", "alert_name": alert.get("alert_name", "?")})
                continue
            heal_action = (mapped["skill"], mapped["operation"], "")

        skill, operation, tier_override = heal_action
        gates = apply_tier_gates(skill, operation)

        # R2 tier: human_confirm=True, auto_heal=False (enforced regardless of rules file)
        if tier_override == "R2" or gates["tier"] == "R2":
            entry: dict[str, Any] = {
                "skill": skill,
                "operation": operation,
                "tier": "R2",
                "risk_tier": "R2",
                "alert_name": alert.get("alert_name", alert.get("id", "?")),
                "action": "escalate",
                "human_confirm": True,
                "auto_heal": False,
                "status": "planned_escalate" if dry_run else "escalated_r2",
                "dry_run": dry_run,
            }
            actions.append(entry)
            continue

        entry = {
            "skill": skill,
            "operation": operation,
            "tier": gates["tier"],
            "risk_tier": gates["tier"],
            "alert_name": alert.get("alert_name", alert.get("id", "?")),
            "action": "observe_heal",
            "human_confirm": gates.get("human_confirm", False),
            "auto_heal": gates.get("auto_heal", True),
            "dry_run": dry_run,
        }

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
    parser.add_argument(
        "--alert-source",
        choices=["mock", "monitor"],
        default="mock",
        help="'mock' reads from --alerts-file; 'monitor' calls az monitor metrics alert list",
    )
    parser.add_argument("--resource-group", default=os.environ.get("AZURE_RESOURCE_GROUP", ""))
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run non-R2 observe via auto_feedback_loop (default is plan-only)",
    )
    parser.add_argument(
        "--use-alert-rules",
        action="store_true",
        help="Use alert_rules.json for alert-to-heal mapping instead of SYMPTOM_MAP",
    )
    args = parser.parse_args()
    dry_run = not args.execute

    alerts: list[dict] = []
    if args.alerts_file:
        if args.alert_source != "mock":
            print(" --alerts-file is only valid with --alert-source mock", file=sys.stderr)
            sys.exit(1)
        alerts = json.loads(args.alerts_file.read_text(encoding="utf-8"))
        if not isinstance(alerts, list):
            print("alerts-file must be a JSON list", file=sys.stderr)
            sys.exit(1)
    elif args.alert_source == "monitor":
        if not args.resource_group:
            print("Need --resource-group or AZURE_RESOURCE_GROUP", file=sys.stderr)
            sys.exit(1)
        alerts = _fetch_monitor_alerts(args.resource_group)
    else:
        print("Provide --alerts-file (mock) or --alert-source monitor", file=sys.stderr)
        sys.exit(1)

    actions = process_alerts(
        alerts, dry_run=dry_run, resource_group=args.resource_group,
        use_alert_rules=args.use_alert_rules,
    )
    out = {
        "time": datetime.now(timezone.utc).isoformat(),
        "alert_count": len(alerts),
        "alert_source": args.alert_source,
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
