"""Tests for scripts/run_all_scenarios.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure scripts/ is importable (mirrors test_mock_azure.py approach)
sys.path.insert(0, "scripts")
from mock_azure import MockAzure  # noqa: E402
from run_all_scenarios import (  # noqa: E402
    OUTPUT_REPORT,
    SCENARIOS_DIR,
    detect_service,
    generate_report,
    run_all_scenarios,
)


def test_run_all_scenarios_importable() -> None:
    """1. Module can be imported without errors."""
    import run_all_scenarios  # type: ignore[import-untyped]  # noqa: F811


def test_run_all_scenarios_returns_dict() -> None:
    """2. run_all_scenarios returns correct structure."""
    mock = MockAzure()
    results = run_all_scenarios(mock, SCENARIOS_DIR)
    assert isinstance(results, dict)
    assert "total_scenarios" in results
    assert "passed" in results
    assert "failed" in results
    assert "results" in results
    assert isinstance(results["results"], list)
    assert results["total_scenarios"] >= 0
    assert results["passed"] >= 0
    assert results["failed"] >= 0

    # Check each result entry has required fields
    for r in results["results"]:
        assert "skill" in r
        assert "scenario" in r
        assert "expected" in r
        assert "actual" in r
        assert "passed" in r
        assert "commands" in r


def test_all_24_scenarios_executed() -> None:
    """3. All 24 scenarios are executed."""
    mock = MockAzure()
    results = run_all_scenarios(mock, SCENARIOS_DIR)
    assert results["total_scenarios"] == 24
    assert len(results["results"]) == 24

    # Verify all 8 skills are present
    skills = {r["skill"] for r in results["results"]}
    expected_skills = {
        "azure-aks-ops",
        "azure-appgateway-ops",
        "azure-blobstorage-ops",
        "azure-frontdoor-ops",
        "azure-keyvault-ops",
        "azure-loadbalancer-ops",
        "azure-vm-ops",
        "azure-vnet-ops",
    }
    assert skills == expected_skills


def test_normal_scenarios_pass() -> None:
    """4. Normal scenarios all pass."""
    mock = MockAzure()
    results = run_all_scenarios(mock, SCENARIOS_DIR)
    normal = [r for r in results["results"] if r["expected"] == "success"]
    assert len(normal) == 8  # 8 skills * 1 normal scenario each
    for r in normal:
        assert r["passed"], f"{r['skill']}/{r['scenario']} failed"


def test_full_failure_detected() -> None:
    """5. Full_failure scenarios correctly detect failure (exit_code=1 on first cmd)."""
    mock = MockAzure()
    results = run_all_scenarios(mock, SCENARIOS_DIR)
    full_fails = [r for r in results["results"] if r["expected"] == "full_fail"]
    assert len(full_fails) == 8  # 8 skills * 1 full_fail scenario each
    for r in full_fails:
        assert r["passed"], f"{r['skill']}/{r['scenario']} should be passed"
        assert r["commands"][0]["exit_code"] == 1, (
            f"{r['skill']}/{r['scenario']}: first command should have exit_code 1"
        )


def test_report_file_created(tmp_path: Path) -> None:
    """6. Report file is created with correct content."""
    mock = MockAzure()
    results = run_all_scenarios(mock, SCENARIOS_DIR)
    report = generate_report(results)
    report_path = tmp_path / "l4-verify-2026-Q3.md"
    report_path.write_text(report, encoding="utf-8")

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# L4 验证报告" in content
    assert "## 汇总" in content
    assert "| 总场景数 | 24 |" in content
    assert "## 逐技能详情" in content
    assert "✅" in content  # at least one pass mark


def test_detect_service() -> None:
    """detect_service correctly identifies service from az command."""
    assert detect_service("az vm create --name x --resource-group r") == "vm"
    assert detect_service("az aks show --name x --resource-group r") == "aks"
    assert detect_service("az network lb list --resource-group r") == "lb"
    assert detect_service("az network vnet show --name x --resource-group r") == "vnet"
    assert (
        detect_service("az network application-gateway show --name x --resource-group r")
        == "application-gateway"
    )
    assert detect_service("az storage account list") == "storage"
    assert detect_service("az keyvault show --name x --resource-group r") == "keyvault"
    assert detect_service("az afd profile show --profile-name x --resource-group r") == "afd"
    assert detect_service("echo hello") == "unknown"


def test_partial_failure_scenarios_pass() -> None:
    """Partial failure scenarios correctly fail at specified index and pass others.

    Note: some scenario commands naturally fail because the MockAzure does not
    implement all subcommands (e.g. ``create`` for many services). This test
    verifies that:
    - The scenario result is marked as passed (expected == actual)
    - The failure injection changes the exit_code at fail_at indices
    """
    mock = MockAzure()
    results = run_all_scenarios(mock, SCENARIOS_DIR)
    partial = [r for r in results["results"] if r["expected"] == "partial_fail"]
    assert len(partial) == 8

    # Load scenario files to check fail_at indices
    for scenario_result in partial:
        skill = scenario_result["skill"]
        assert scenario_result["passed"], f"{skill}/partial_failure should pass"

        skill_file = SCENARIOS_DIR / f"{skill}.json"
        with open(skill_file, encoding="utf-8") as f:
            data = json.load(f)
        scenario_def = next(
            s for s in data["scenarios"] if s["name"] == scenario_result["scenario"]
        )
        fail_indices = set(scenario_def.get("fail_at", []))

        # Run the same scenario WITHOUT failure injection to get baseline
        baseline_mock = MockAzure()
        baseline_results: list[dict] = []
        for cmd in scenario_def["commands"]:
            baseline_results.append(baseline_mock.execute(cmd))

        # Verify that failure injection changes exit_code at fail_at indices
        for i, cmd_result in enumerate(scenario_result["commands"]):
            if i in fail_indices:
                # With failure injection, exit_code should differ from baseline
                if baseline_results[i]["exit_code"] == 0:
                    assert cmd_result["exit_code"] == 1, (
                        f"{skill}/partial_failure cmd[{i}] should fail with injection"
                    )
                # If baseline was already 1 (mock limitation), injection doesn't change it
            else:
                # Non-fail_at commands should have same behavior as baseline
                assert cmd_result["exit_code"] == baseline_results[i]["exit_code"], (
                    f"{skill}/partial_failure cmd[{i}] exit_code changed unexpectedly: "
                    f"{baseline_results[i]['exit_code']} -> {cmd_result['exit_code']}"
                )
