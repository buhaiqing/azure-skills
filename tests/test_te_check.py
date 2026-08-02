"""Tests for TE (Token Efficiency) checker - TDD approach"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from te_check import (
    check_skill,
    TEViolation,
    check_te1_static_tables,
    check_te2_docstrings,
    check_te3_error_tables,
    check_te4_json_paths,
    check_te5_yaml_anchors,
    check_te6_cross_file_dup,
    check_te7_content分层,
)


def test_te_check_imports():
    """TE checker should be importable"""
    assert check_skill is not None
    assert TEViolation is not None




def test_te1_detects_hardcoded_version():
    """TE-1: Should detect hardcoded version numbers outside frontmatter"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "azure-test-ops"
        skill_dir.mkdir()
        
        # Create SKILL.md with hardcoded version in body (not frontmatter)
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test
---

# Test Skill

## Overview
API version: 2024-01-01
""")
        
        violations = check_te1_static_tables(skill_dir)
        assert len(violations) > 0
        assert violations[0].rule == "TE-1"


def test_te1_ignores_frontmatter_version():
    """TE-1: Should NOT flag version in YAML frontmatter"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "azure-test-ops"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test
version: "1.0.0"
---

# Test Skill

No hardcoded versions here.
""")
        
        violations = check_te1_static_tables(skill_dir)
        assert len(violations) == 0


def test_te1_detects_hardcoded_quota():
    """TE-1: Should detect hardcoded quota values"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "azure-test-ops"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test
---

# Test Skill

## Limits
quota: 100
""")
        
        violations = check_te1_static_tables(skill_dir)
        assert len(violations) > 0
        assert violations[0].rule == "TE-1"


def test_te2_detects_excessive_docstrings():
    """TE-2: Should detect functions with docstrings in code blocks"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "azure-test-ops"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test
---

# Test Skill

```python
def my_function():
    \"\"\"This is a docstring that should be flagged.\"\"\"
    pass
```
""")
        
        violations = check_te2_docstrings(skill_dir)
        assert len(violations) > 0
        assert violations[0].rule == "TE-2"


def test_te3_detects_wide_error_tables():
    """TE-3: Should detect error tables with more than 3 columns"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "azure-test-ops"
        skill_dir.mkdir()
        
        ref_dir = skill_dir / "references"
        ref_dir.mkdir()
        
        troubleshooting = ref_dir / "troubleshooting.md"
        troubleshooting.write_text("""# Troubleshooting

| Error Code | Description | Cause | Solution | Extra Column |
|------------|-------------|-------|----------|--------------|
| ERR001 | Error 1 | Cause 1 | Fix 1 | Extra 1 |
""")
        
        violations = check_te3_error_tables(skill_dir)
        assert len(violations) > 0
        assert violations[0].rule == "TE-3"


def test_te3_accepts_narrow_error_tables():
    """TE-3: Should accept error tables with 3 or fewer columns"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "azure-test-ops"
        skill_dir.mkdir()
        
        ref_dir = skill_dir / "references"
        ref_dir.mkdir()
        
        troubleshooting = ref_dir / "troubleshooting.md"
        troubleshooting.write_text("""# Troubleshooting

| Error Code | Description | Solution |
|------------|-------------|----------|
| ERR001 | Error 1 | Fix 1 |
""")
        
        violations = check_te3_error_tables(skill_dir)
        assert len(violations) == 0


def test_te4_detects_repeated_json_paths():
    """TE-4: Should detect JSON paths repeated more than 3 times"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "azure-test-ops"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test
---

# Test Skill

## Examples
```bash
az vm show --query "properties.provisioningState"
az vm show --query "properties.provisioningState"
az vm show --query "properties.provisioningState"
az vm show --query "properties.provisioningState"
```
""")
        
        violations = check_te4_json_paths(skill_dir)
        assert len(violations) > 0
        assert violations[0].rule == "TE-4"
        assert violations[0].fixable is True


def test_te4_accepts_few_repetitions():
    """TE-4: Should accept JSON paths repeated 3 or fewer times"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "azure-test-ops"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test
---

# Test Skill

## Examples
```bash
az vm show --query "properties.provisioningState"
az vm show --query "properties.provisioningState"
az vm show --query "properties.powerState"
```
""")
        
        violations = check_te4_json_paths(skill_dir)
        assert len(violations) == 0


def test_te5_detects_yaml_duplication():
    """TE-5: Should detect duplicate YAML configurations"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "azure-test-ops"
        skill_dir.mkdir()
        
        assets_dir = skill_dir / "assets"
        assets_dir.mkdir()
        
        example_config = assets_dir / "example-config.yaml"
        example_config.write_text("""# Config
resource_group: my-rg
location: eastus
resource_group: my-rg
location: eastus
""")
        
        violations = check_te5_yaml_anchors(skill_dir)
        assert len(violations) > 0
        assert violations[0].rule == "TE-5"
        assert violations[0].fixable is True


def test_te6_detects_cross_file_duplication():
    """TE-6: Should detect content duplication between SKILL.md and references/"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "azure-test-ops"
        skill_dir.mkdir()
        
        ref_dir = skill_dir / "references"
        ref_dir.mkdir()
        
        # Same content in both files
        duplicate_content = """This is duplicate content that appears in both files.
It should be detected by TE-6 checker.
Multiple lines of duplication make it worse.
And worse.
And even worse.
And more.
"""
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(f"""---
name: test
---

# Test Skill

{duplicate_content}
""")
        
        core_concepts = ref_dir / "core-concepts.md"
        core_concepts.write_text(f"""# Core Concepts

{duplicate_content}
""")
        
        violations = check_te6_cross_file_dup(skill_dir)
        assert len(violations) > 0
        assert violations[0].rule == "TE-6"


def test_te7_detects_deep_content_in_skill():
    """TE-7: Should detect deep analysis content in SKILL.md"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "azure-test-ops"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test
---

# Test Skill

## AIOps
This is deep analysis content that should be in references/.
""")
        
        violations = check_te7_content分层(skill_dir)
        assert len(violations) > 0
        assert violations[0].rule == "TE-7"


def test_check_skill_runs_all_checks():
    """check_skill should run all TE checks and aggregate violations"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "azure-test-ops"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test
---

# Test Skill

## AIOps
Deep content here.

quota: 100
""")
        
        violations = check_skill(skill_dir)
        # Should have at least TE-1 (quota) and TE-7 (AIOps)
        rules = {v.rule for v in violations}
        assert "TE-1" in rules or "TE-7" in rules


def test_check_skill_handles_missing_files():
    """check_skill should handle missing files gracefully"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "azure-test-ops"
        skill_dir.mkdir()
        
        # No files created - should not crash
        violations = check_skill(skill_dir)
        assert violations == []
