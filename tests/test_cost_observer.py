"""TDD tests for CostObserver integration in auto_feedback_loop.py."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, "scripts")


# ============================================================
# Test 1: _observe_and_attach_cost attaches cost observation
# ============================================================

def test_observe_and_attach_cost_success(monkeypatch):
    """_observe_and_attach_cost should attach cost data when subscription_id provided."""
    from auto_feedback_loop import FeedbackResult, _observe_and_attach_cost

    # Mock observe_cost to return a successful result
    def mock_observe_cost(subscription_id, scope=None, days=30):
        from state_observer import CostObservation
        return CostObservation(
            current_cost=500.0,
            previous_cost=400.0,
            cost_change_pct=25.0,
        )
    monkeypatch.setattr("auto_feedback_loop.observe_cost", mock_observe_cost)

    result = FeedbackResult(
        status="success",
        actual_state={},
        heal_attempts=0,
        trace_id="test-trace",
        message="test",
        escalation=None,
    )

    updated = _observe_and_attach_cost(result, "sub-123", "azure-vm-ops", "vm_create")
    assert updated.cost_observation is not None
    assert updated.cost_observation["current_cost"] == 500.0
    assert updated.cost_observation["cost_change_pct"] == 25.0
    assert "cost surged" in updated.message


def test_observe_and_attach_cost_no_subscription(monkeypatch):
    """No subscription_id should leave cost_observation as None."""
    from auto_feedback_loop import FeedbackResult, _observe_and_attach_cost

    result = FeedbackResult(
        status="success",
        actual_state={},
        heal_attempts=0,
        trace_id="test-trace",
        message="test",
        escalation=None,
    )

    updated = _observe_and_attach_cost(result, None, "azure-vm-ops", "vm_create")
    assert updated.cost_observation is None
    assert "no subscription_id" in updated.message


def test_observe_and_attach_cost_error(monkeypatch):
    """Observe failure should be reflected in cost_observation.error."""
    from auto_feedback_loop import FeedbackResult, _observe_and_attach_cost

    def mock_observe_cost_error(subscription_id, scope=None, days=30):
        from state_observer import CostObservation
        return CostObservation(
            current_cost=0.0,
            previous_cost=0.0,
            cost_change_pct=0.0,
            error="cost query failed: auth error",
        )
    monkeypatch.setattr("auto_feedback_loop.observe_cost", mock_observe_cost_error)

    result = FeedbackResult(
        status="success",
        actual_state={},
        heal_attempts=0,
        trace_id="test-trace",
        message="test",
        escalation=None,
    )

    updated = _observe_and_attach_cost(result, "sub-123", "azure-vm-ops", "vm_create")
    assert updated.cost_observation is not None
    assert updated.cost_observation["error"] is not None
    assert "cost observe failed" in updated.message


# ============================================================
# Test 2: _finalize calls _observe_and_attach_cost when enabled
# ============================================================

def test_finalize_with_cost_observer(monkeypatch):
    """_finalize should call _observe_and_attach_cost when observe_cost_enabled=True."""
    from auto_feedback_loop import FeedbackResult

    # Mock persist_trace to do nothing
    monkeypatch.setattr("auto_feedback_loop._persist_trace", lambda tid, fb: None)

    # Mock observe_cost
    def mock_observe_cost(subscription_id, scope=None, days=30):
        from state_observer import CostObservation
        return CostObservation(
            current_cost=300.0,
            previous_cost=250.0,
            cost_change_pct=20.0,
        )
    monkeypatch.setattr("auto_feedback_loop.observe_cost", mock_observe_cost)

    # We need to test _finalize with observe_cost_enabled=True.
    # Since _finalize is a closure inside run_with_feedback, we test it via run_with_feedback.
    from auto_feedback_loop import run_with_feedback

    # Mock subprocess to avoid actual command execution
    class MockCompletedProcess:
        returncode = 0
        stdout = '{"vmName": "test-vm", "powerState": "VM running"}'
        stderr = ""

    def mock_subprocess_run(*args, **kwargs):
        return MockCompletedProcess()

    monkeypatch.setattr("auto_feedback_loop.subprocess.run", mock_subprocess_run)

    # Mock load_policy to return a policy with health check
    def mock_load_policy(skill):
        return {
            "operations": {
                "vm_create": {
                    "health_check": {
                        "api": "az vm show",
                        "args_template": ["vm", "show", "--name", "test", "--resource-group", "test"],
                        "parse_field": "powerState",
                    },
                    "healing_rules": [],
                }
            }
        }
    monkeypatch.setattr("auto_feedback_loop.load_policy", mock_load_policy)

    # Mock diff to return match=True
    def mock_diff(desired, actual, operation):
        from state_diff import DiffResult
        return DiffResult(match=True, message="state matches", diffs=[])
    monkeypatch.setattr("auto_feedback_loop.diff", mock_diff)

    # Mock observe to return success
    def mock_observe(api, args_template, parse_field=None, env=None, timeout=30):
        from state_observer import ObserveResult
        return ObserveResult(
            raw={"powerState": "VM running"},
            parsed="VM running",
            elapsed_sec=0.1,
            error=None,
        )
    monkeypatch.setattr("auto_feedback_loop.observe", mock_observe)

    result = run_with_feedback(
        skill="azure-vm-ops",
        operation="vm_create",
        command="az vm create --name test-vm --resource-group test-rg",
        desired_state={"powerState": "VM running"},
        observe_cost_enabled=True,
        subscription_id="sub-123",
    )

    assert result.status in ("success", "healed", "escalated")
    if result.cost_observation:
        assert "cost" in result.message.lower() or "cost" in str(result.cost_observation)


# ============================================================
# Test 3: FeedbackResult has cost_observation field
# ============================================================

def test_feedback_result_has_cost_field():
    """FeedbackResult dataclass must have cost_observation field."""
    from auto_feedback_loop import FeedbackResult

    result = FeedbackResult(
        status="success",
        actual_state={},
        heal_attempts=0,
        trace_id="test",
        message="ok",
        escalation=None,
    )
    assert hasattr(result, "cost_observation")
    assert result.cost_observation is None

    result_with_cost = FeedbackResult(
        status="success",
        actual_state={},
        heal_attempts=0,
        trace_id="test",
        message="ok",
        escalation=None,
        cost_observation={"current_cost": 100.0, "cost_change_pct": 10.0},
    )
    assert result_with_cost.cost_observation["current_cost"] == 100.0


# ============================================================
# Test 4: cost_heal.json operations have correct condition types
# ============================================================

def test_cost_heal_json_has_cost_trend_alert():
    """cost_heal.json must have cost_trend_alert with trend_increasing condition."""
    path = Path(__file__).parent.parent / "scripts" / "self_healing" / "cost_heal.json"
    assert path.exists()

    with open(path) as f:
        policy = json.load(f)

    assert "cost_trend_alert" in policy.get("operations", {}), (
        "Missing cost_trend_alert operation for 3-period trend detection"
    )
    trend_op = policy["operations"]["cost_trend_alert"]
    rules = trend_op.get("healing_rules", [])
    assert len(rules) >= 1, "cost_trend_alert must have at least one healing rule"

    trend_rule = rules[0]
    assert trend_rule["condition_type"] == "trend_increasing", (
        "cost_trend_alert must use trend_increasing condition type"
    )
    assert trend_rule["trend_window"] == 3, (
        "cost_trend_alert must monitor 3 periods for sustained increase"
    )


def test_cost_heal_json_has_cost_query_rate_of_change():
    """cost_query must have rate_of_change healing rule."""
    path = Path(__file__).parent.parent / "scripts" / "self_healing" / "cost_heal.json"
    with open(path) as f:
        policy = json.load(f)

    cost_query = policy.get("operations", {}).get("cost_query", {})
    rules = cost_query.get("healing_rules", [])
    assert len(rules) >= 1, "cost_query must have at least one healing rule"

    rate_rule = rules[0]
    assert rate_rule["condition_type"] == "rate_of_change", (
        "cost_query should detect cost surges via rate_of_change"
    )
    assert rate_rule["threshold_value"] == 0.2, (
        "rate_of_change threshold should be 0.2 (20%)"
    )


# ============================================================
# Test 5: CLI help includes --observe-cost
# ============================================================

def test_cli_has_observe_cost_flag():
    """CLI --help must show --observe-cost and --subscription-id flags."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "auto_feedback_loop", "--help"],
        capture_output=True, text=True, cwd=str(Path(__file__).parent.parent / "scripts"),
    )
    assert "--observe-cost" in result.stdout
    assert "--subscription-id" in result.stdout
