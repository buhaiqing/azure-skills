"""Tests for risk_tiers and live_canary (MS L400)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from risk_tiers import apply_tier_gates, resolve_tier  # noqa: E402
from live_canary import run_canary  # noqa: E402


def test_vm_delete_is_r2():
    assert resolve_tier("azure-vm-ops", "vm_delete") == "R2"
    gates = apply_tier_gates("azure-vm-ops", "vm_delete")
    assert gates["force_risky"] is True
    assert gates["auto_heal"] is False
    assert gates["max_heal_attempts"] == 0


def test_vm_list_is_r0():
    assert resolve_tier("azure-vm-ops", "vm_list") == "R0"
    gates = apply_tier_gates("azure-vm-ops", "vm_list")
    assert gates["human_confirm"] is False
    assert gates["auto_heal"] is True


def test_keyword_fallback_delete():
    assert resolve_tier("azure-unknown-ops", "something_delete") == "R2"


def test_live_canary_dry_run():
    summary = run_canary(dry_run=True, env_mode="mock")
    assert summary["total"] == 8
    assert summary["failed"] == 0
    assert all(r["status"] == "dry_run_ok" for r in summary["results"])


def test_watch_and_heal_sample():
    sys.path.insert(0, str(SCRIPTS))
    from watch_and_heal import process_alerts

    alerts = json.loads((SCRIPTS / "sample_alerts.json").read_text(encoding="utf-8"))
    actions = process_alerts(alerts, dry_run=True)
    assert len(actions) == 3
    statuses = {a.get("status") for a in actions}
    assert "unmapped" in statuses
    assert "planned" in statuses
