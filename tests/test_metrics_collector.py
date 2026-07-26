"""Tests for scripts/metrics_collector.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure scripts/ is importable (mirrors test_mock_azure.py approach)
sys.path.insert(0, "scripts")
from metrics_collector import MetricsCollector  # noqa: E402


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

SAMPLE_REPORT = """# L4 验证报告 — 2026-Q3

> 生成时间: 2026-07-26T15:53:39+00:00

## 汇总

| 指标 | 值 |
|------|-----|
| 总场景数 | 24 |
| 通过 | 24 |
| 失败 | 0 |
| 通过率 | 100.0% |

## 逐技能详情

### azure-aks-ops

| 场景 | 预期 | 实际 | 结果 |
|------|------|------|------|
| normal_operation | success | success | ✅ |
| partial_failure | partial_fail | partial_fail | ✅ |
| full_failure | full_fail | full_fail | ✅ |

### azure-appgateway-ops

| 场景 | 预期 | 实际 | 结果 |
|------|------|------|------|
| normal_operation | success | success | ✅ |
| partial_failure | partial_fail | partial_fail | ✅ |
| full_failure | full_fail | full_fail | ✅ |

### azure-blobstorage-ops

| 场景 | 预期 | 实际 | 结果 |
|------|------|------|------|
| normal_operation | success | success | ✅ |
| partial_failure | partial_fail | partial_fail | ✅ |
| full_failure | full_fail | full_fail | ✅ |

### azure-frontdoor-ops

| 场景 | 预期 | 实际 | 结果 |
|------|------|------|------|
| normal_operation | success | success | ✅ |
| partial_failure | partial_fail | partial_fail | ✅ |
| full_failure | full_fail | full_fail | ✅ |

### azure-keyvault-ops

| 场景 | 预期 | 实际 | 结果 |
|------|------|------|------|
| normal_operation | success | success | ✅ |
| partial_failure | partial_fail | partial_fail | ✅ |
| full_failure | full_fail | full_fail | ✅ |

### azure-loadbalancer-ops

| 场景 | 预期 | 实际 | 结果 |
|------|------|------|------|
| normal_operation | success | success | ✅ |
| partial_failure | partial_fail | partial_fail | ✅ |
| full_failure | full_fail | full_fail | ✅ |

### azure-vm-ops

| 场景 | 预期 | 实际 | 结果 |
|------|------|------|------|
| normal_operation | success | success | ✅ |
| partial_failure | partial_fail | partial_fail | ✅ |
| full_failure | full_fail | full_fail | ✅ |

### azure-vnet-ops

| 场景 | 预期 | 实际 | 结果 |
|------|------|------|------|
| normal_operation | success | success | ✅ |
| partial_failure | partial_fail | partial_fail | ✅ |
| full_failure | full_fail | full_fail | ✅ |

## 失败详情

（无失败场景）
"""


@pytest.fixture
def sample_report(tmp_path) -> str:
    """Write the sample report to a temp file and return its path."""
    report_file = tmp_path / "benchmark" / "l4-verify-2026-Q3.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(SAMPLE_REPORT, encoding="utf-8")
    return str(report_file)


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


def test_metrics_collector_importable():
    """1. Module can be imported."""
    from metrics_collector import MetricsCollector  # noqa: F811

    assert MetricsCollector is not None


def test_collect_returns_dict(sample_report):
    """2. collect() returns a dict with the expected top-level keys."""
    collector = MetricsCollector(sample_report)
    result = collector.collect()
    assert isinstance(result, dict)
    assert "report_time" in result
    assert "total_scenarios" in result
    assert "passed" in result
    assert "failed" in result
    assert "metrics" in result
    assert "l4_targets" in result
    assert "by_skill" in result


def test_all_scenarios_counted(sample_report):
    """3. All 24 scenarios are counted."""
    collector = MetricsCollector(sample_report)
    result = collector.collect()
    assert result["total_scenarios"] == 24
    assert result["passed"] == 24
    assert result["failed"] == 0


def test_safety_pass_rate(sample_report):
    """4. Safety pass rate is 100% when all scenarios pass with safety."""
    collector = MetricsCollector(sample_report)
    result = collector.collect()
    assert result["metrics"]["safety_pass_rate"] == 100.0


def test_auto_heal_rate(sample_report):
    """5. Auto-heal success rate is 100% when all 24 scenarios pass."""
    collector = MetricsCollector(sample_report)
    result = collector.collect()
    # All 24 scenarios pass (actual == expected) → 100%
    assert result["metrics"]["auto_heal_success_rate"] == 100.0


def test_export_json(sample_report, tmp_path):
    """6. export_json creates a valid JSON file."""
    output = tmp_path / "l4-health-report.json"
    collector = MetricsCollector(sample_report)
    collector.export_json(str(output))
    assert output.exists()
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["total_scenarios"] == 24


def test_l4_targets_met(sample_report):
    """7. L4 target checks are correct."""
    collector = MetricsCollector(sample_report)
    result = collector.collect()
    targets = result["l4_targets"]

    # safety_pass_rate target 100, actual 100 → met
    assert targets["safety_pass_rate"]["met"] is True

    # auto_heal_success_rate target 85, actual 100.0 → met
    assert targets["auto_heal_success_rate"]["met"] is True

    # escalation_rate target 15, actual 0.0 → met (0 failed scenarios)
    assert targets["escalation_rate"]["met"] is True
