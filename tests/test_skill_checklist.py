"""Tests for skill_checklist.py — 新 skill 8 步检查清单自动化验证"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from skill_checklist import (
    check_step1_triggers,
    check_step2_size,
    check_step3_credentials,
    check_step4_destructive,
    check_step5_flow,
    check_step6_dual_path,
    check_step7_cadl,
    check_step8_references,
    check_skill_checklist,
    ChecklistViolation,
)


def _make_skill(tmpdir, name="azure-test-ops", skill_md="", files=None):
    """Helper to create a minimal skill directory."""
    skill_dir = Path(tmpdir) / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
    if files:
        for rel_path, content in files.items():
            p = skill_dir / rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    return skill_dir


# ── Step 1: Triggers ──────────────────────────────────────────────

def test_step1_pass_with_should_and_should_not():
    skill_md = """---
name: test
---
### SHOULD Use When
- User mentions Azure Test

### SHOULD NOT Use When
- Billing only → delegate to: `azure-cost-ops`
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step1_triggers(sd)
        assert len(violations) == 0


def test_step1_fail_missing_should_not():
    skill_md = """---
name: test
---
### SHOULD Use When
- User mentions Azure Test
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step1_triggers(sd)
        assert len(violations) > 0
        assert violations[0].step == 1


def test_step1_fail_missing_should():
    skill_md = """---
name: test
---
### SHOULD NOT Use When
- Billing only
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step1_triggers(sd)
        assert len(violations) > 0


# ── Step 2: SKILL.md size ─────────────────────────────────────────

def test_step2_pass_within_range():
    # Generate exactly 120 lines
    lines = "\n".join([f"# Line {i}" for i in range(120)])
    skill_md = f"---\nname: test\n---\n{lines}"
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step2_size(sd)
        assert len(violations) == 0


def test_step2_fail_too_long():
    # Generate 200 lines (exceeds 150)
    lines = "\n".join([f"# Line {i}" for i in range(200)])
    skill_md = f"---\nname: test\n---\n{lines}"
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step2_size(sd)
        assert len(violations) > 0
        assert violations[0].step == 2


def test_step2_fail_too_short():
    skill_md = "---\nname: test\n---\n# Too short"
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step2_size(sd)
        assert len(violations) > 0


# ── Step 3: Credentials ───────────────────────────────────────────

def test_step3_pass_env_placeholders():
    skill_md = """---
name: test
---
Use `{{env.AZURE_SUBSCRIPTION_ID}}` for subscription.
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step3_credentials(sd)
        assert len(violations) == 0


def test_step3_fail_literal_secret():
    skill_md = """---
name: test
---
Set your subscription ID: 12345678-1234-1234-1234-123456789abc
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step3_credentials(sd)
        assert len(violations) > 0
        assert violations[0].step == 3


def test_step3_fail_ask_user_for_secret():
    skill_md = """---
name: test
---
Please paste your AZURE_CLIENT_SECRET here:
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step3_credentials(sd)
        assert len(violations) > 0


# ── Step 4: Destructive ops safety gate ───────────────────────────

def test_step4_pass_delete_with_confirmation():
    skill_md = """---
name: test
---
### Operation: Delete Resource
**Safety Gate**: MUST obtain explicit user confirmation before deletion.
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step4_destructive(sd)
        assert len(violations) == 0


def test_step4_fail_delete_without_confirmation():
    skill_md = """---
name: test
---
### Operation: Delete Resource
```bash
az vm delete --name myvm --resource-group myrg --yes
```
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step4_destructive(sd)
        assert len(violations) > 0
        assert violations[0].step == 4


def test_step4_skip_when_no_destructive():
    skill_md = """---
name: test
---
### Operation: List Resources
```bash
az vm list --output json
```
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step4_destructive(sd)
        assert len(violations) == 0


# ── Step 5: Execution flow ────────────────────────────────────────

def test_step5_pass_with_flow_keywords():
    skill_md = """---
name: test
---
## Pre-flight
Check quota.

## Execute
Run az command.

## Validate
Poll for completion.

## Recover
Handle errors.
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step5_flow(sd)
        assert len(violations) == 0


def test_step5_fail_missing_flow():
    skill_md = """---
name: test
---
## Overview
This skill does stuff.
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step5_flow(sd)
        assert len(violations) > 0
        assert violations[0].step == 5


# ── Step 6: Dual-path (CLI + SDK) ─────────────────────────────────

def test_step6_pass_with_cli_and_sdk():
    skill_md = """---
name: test
---
#### Execute — Azure CLI (Primary)
```bash
az vm show --output json
```

#### Execute — Azure SDK (Fallback)
```python
from azure.mgmt.compute import ComputeManagementClient
```
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step6_dual_path(sd)
        assert len(violations) == 0


def test_step6_fail_cli_only():
    skill_md = """---
name: test
---
#### Execute — Azure CLI (Primary)
```bash
az vm show --output json
```
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step6_dual_path(sd)
        assert len(violations) > 0
        assert violations[0].step == 6


# ── Step 7: CADL trigger ──────────────────────────────────────────

def test_step7_pass_with_cadl():
    skill_md = """---
name: test
---
# Skill

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step7_cadl(sd)
        assert len(violations) == 0


def test_step7_fail_missing_cadl():
    skill_md = """---
name: test
---
# Skill
No CADL here.
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md)
        violations = check_step7_cadl(sd)
        assert len(violations) > 0
        assert violations[0].step == 7


# ── Step 8: Reference files ───────────────────────────────────────

def test_step8_pass_with_all_references():
    skill_md = """---
name: test
---
## Reference Files
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration](references/integration.md)
"""
    files = {
        "references/core-concepts.md": "# Core",
        "references/troubleshooting.md": "# Troubleshoot",
        "references/integration.md": "# Integration",
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md, files=files)
        violations = check_step8_references(sd)
        assert len(violations) == 0


def test_step8_fail_missing_reference_file():
    skill_md = """---
name: test
---
## Reference Files
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
"""
    files = {
        "references/core-concepts.md": "# Core",
        # troubleshooting.md is missing!
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md, files=files)
        violations = check_step8_references(sd)
        assert len(violations) > 0
        assert violations[0].step == 8


# ── Full checklist ────────────────────────────────────────────────

def test_check_skill_checklist_full_pass():
    """A well-formed skill should pass all 8 steps."""
    # Pad to meet 80-line minimum (real skills are 100-150 lines)
    padding = "\n".join([f"## Section {i}\nContent for section {i}." for i in range(1, 25)])
    skill_md = f"""---
name: test
---
### SHOULD Use When
- User mentions Azure Test

### SHOULD NOT Use When
- Billing only → delegate to: `azure-cost-ops`

Use `{{{{env.AZURE_SUBSCRIPTION_ID}}}}` for subscription.

### Operation: Delete Resource
**Safety Gate**: MUST obtain explicit user confirmation before deletion.

## Pre-flight
Check quota.

## Execute — Azure CLI (Primary)
```bash
az vm show --output json
```

## Execute — Azure SDK (Fallback)
```python
from azure.mgmt.compute import ComputeManagementClient
```

## Validate
Poll for completion.

## Recover
Handle errors.

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。

## Reference Files
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration](references/integration.md)

{padding}
"""
    files = {
        "references/core-concepts.md": "# Core",
        "references/troubleshooting.md": "# Troubleshoot",
        "references/integration.md": "# Integration",
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = _make_skill(tmpdir, skill_md=skill_md, files=files)
        violations = check_skill_checklist(sd)
        assert len(violations) == 0


def test_check_skill_checklist_missing_files_graceful():
    """Should not crash if SKILL.md is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = Path(tmpdir) / "azure-test-ops"
        sd.mkdir()
        violations = check_skill_checklist(sd)
        # Should return violations (missing SKILL.md) but not crash
        assert isinstance(violations, list)
