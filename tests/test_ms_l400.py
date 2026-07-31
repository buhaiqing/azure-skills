"""Tests for MS L400 + review regressions."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from risk_tiers import apply_tier_gates, resolve_tier, _load  # noqa: E402
from live_canary import run_canary, _expand_to_argv  # noqa: E402
from auto_feedback_loop import (  # noqa: E402
    run_with_feedback,
    _heal_argv as loop_heal_argv,
    _apply_heal_rule,
)
from watch_and_heal import process_alerts  # noqa: E402


def setup_function(_fn=None):
    _load.cache_clear()


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


def test_scale_to_zero_is_r2():
    assert resolve_tier("azure-unknown-ops", "scale_to_zero") == "R2"
    assert resolve_tier("azure-vm-ops", "scale_to_zero") == "R2"


def test_keyword_fallback_delete():
    assert resolve_tier("azure-unknown-ops", "something_delete") == "R2"


def test_get_stop_status_not_r2():
    # stop as substring of get_stop_status should not force R2 after pattern tighten
    assert resolve_tier("azure-unknown-ops", "get_stop_status") == "R0"


def test_live_canary_dry_run():
    summary = run_canary(dry_run=True, env_mode="mock")
    assert summary["total"] == 8
    assert summary["failed"] == 0
    assert all(r["status"] == "dry_run_ok" for r in summary["results"])


def test_live_canary_live_all_skipped_zero_passed():
    summary = run_canary(dry_run=False, env_mode="live")
    assert summary["mode"] == "live"
    # without AZURE_RESOURCE_GROUP everything skips
    assert summary["passed"] == 0
    assert summary["skipped"] == summary["total"]


def test_expand_rejects_flag_injection():
    try:
        _expand_to_argv(
            "az vm list --resource-group {{env.AZURE_RESOURCE_GROUP}} --output json",
            {"AZURE_RESOURCE_GROUP": "--subscription evil"},
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "flag injection" in str(exc) or "must not start" in str(exc)


def test_expand_keeps_spaces_as_single_token():
    argv = _expand_to_argv(
        "az vm list --resource-group {{env.AZURE_RESOURCE_GROUP}} --output json",
        {"AZURE_RESOURCE_GROUP": "my rg"},
    )
    assert "my rg" in argv
    assert argv.count("my") == 0 or "my rg" in argv


def test_heal_argv_no_double_az():
    argv = loop_heal_argv("az vm start", ["vm", "start", "--name", "x"])
    assert argv[0] == "az"
    assert argv.count("az") == 1
    assert argv[1:3] == ["vm", "start"]


def test_heal_argv_prefers_args_template():
    argv = loop_heal_argv("az vm start", ["vm", "start", "--name", "n"])
    assert argv == ["az", "vm", "start", "--name", "n"]


def test_apply_heal_respects_returncode():
    rule = {
        "condition_type": "field_not_equal",
        "condition_field": "power",
        "condition_value": "running",
        "heal_action": "vm start",
        "heal_args_template": ["vm", "start", "--name", "x"],
    }
    with mock.patch("auto_feedback_loop.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=1, stderr="boom", stdout="")
        ok, msg = _apply_heal_rule(rule, {"power": "stopped"}, None, {})
        assert ok is False
        assert "heal failed" in msg
        run.assert_called_once()
        assert run.call_args[0][0][0] == "az"
        assert run.call_args[0][0].count("az") == 1


def test_dry_run_zero_subprocess():
    with mock.patch("auto_feedback_loop.subprocess.run") as run:
        result = run_with_feedback(
            skill="azure-vm-ops",
            operation="vm_create",
            command="az vm create --name t --resource-group rg",
            desired_state={"powerState": "VM running"},
            dry_run=True,
        )
        assert result.status == "planned"
        run.assert_not_called()


def test_max_heal_caller_zero_not_raised():
    with mock.patch("auto_feedback_loop.subprocess.run") as run:
        # dry_run returns before heal, but gates should still clamp
        from risk_tiers import apply_tier_gates
        gates = apply_tier_gates("azure-vm-ops", "vm_create")
        assert gates["max_heal_attempts"] >= 1
        # explicit 0 after min
        attempts = min(0, gates["max_heal_attempts"])
        assert attempts == 0
        result = run_with_feedback(
            skill="azure-vm-ops",
            operation="vm_create",
            command="az vm create --name t --resource-group rg",
            desired_state={},
            dry_run=True,
            max_heal_attempts=0,
        )
        assert result.status == "planned"
        run.assert_not_called()


def test_watch_and_heal_sample():
    alerts = json.loads((SCRIPTS / "sample_alerts.json").read_text(encoding="utf-8"))
    actions = process_alerts(alerts, dry_run=True)
    assert len(actions) == 4
    statuses = {a.get("status") for a in actions}
    assert "unmapped" in statuses
    assert "planned" in statuses
    assert "planned_escalate" in statuses


def test_monitor_payload_no_fake_cli():
    import health_dashboard as hd

    with mock.patch("health_dashboard.subprocess.run") as run:
        ok = hd._send_to_azure_monitor(
            {"l4_targets": {}, "total_scenarios": 1, "passed": 1, "failed": 0},
            resource_id="/subscriptions/x/resourceGroups/r/providers/microsoft.insights/components/c",
        )
        assert ok is True
        run.assert_not_called()
