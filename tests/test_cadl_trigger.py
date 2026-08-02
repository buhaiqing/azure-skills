"""Tests for cadl_trigger.py (C-5)"""
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from cadl_trigger import (
    find_skill_files,
    check_cadl_hook,
    inject_cadl_hook,
    CADL_HOOK,
)


def test_find_skill_files():
    """find_skill_files discovers all azure-*-ops/SKILL.md files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create valid skill directories
        (root / "azure-vm-ops").mkdir()
        (root / "azure-vm-ops" / "SKILL.md").write_text("# VM Skill")
        
        (root / "azure-aks-ops").mkdir()
        (root / "azure-aks-ops" / "SKILL.md").write_text("# AKS Skill")
        
        # Create invalid directories (should be ignored)
        (root / "azure-invalid").mkdir()
        (root / "azure-invalid" / "SKILL.md").write_text("# Invalid")
        
        (root / "other-ops").mkdir()
        (root / "other-ops" / "SKILL.md").write_text("# Other")
        
        skill_files = find_skill_files(root)
        
        assert len(skill_files) == 2
        assert all(f.name == "SKILL.md" for f in skill_files)
        assert any("azure-vm-ops" in str(f) for f in skill_files)
        assert any("azure-aks-ops" in str(f) for f in skill_files)


def test_check_cadl_hook_present():
    """check_cadl_hook returns True when CADL reference exists"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_file = Path(tmpdir) / "SKILL.md"
        skill_file.write_text("# Skill\n\nSome content\n\n复利资产沉淀机制")
        
        assert check_cadl_hook(skill_file) is True


def test_check_cadl_hook_absent():
    """check_cadl_hook returns False when no CADL reference"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_file = Path(tmpdir) / "SKILL.md"
        skill_file.write_text("# Skill\n\nSome content without the trigger")
        
        assert check_cadl_hook(skill_file) is False



def test_inject_cadl_hook_new():
    """inject_cadl_hook adds CADL hook to file without it"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_file = Path(tmpdir) / "SKILL.md"
        original_content = "# Skill\n\nSome content\n"
        skill_file.write_text(original_content)
        
        result = inject_cadl_hook(skill_file, dry_run=False)
        
        assert result is True
        new_content = skill_file.read_text()
        assert CADL_HOOK in new_content
        assert original_content.strip() in new_content


def test_inject_cadl_hook_already_present():
    """inject_cadl_hook returns False when hook already exists"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_file = Path(tmpdir) / "SKILL.md"
        skill_file.write_text(f"# Skill\n\n{CADL_HOOK}\n")
        
        result = inject_cadl_hook(skill_file, dry_run=False)
        
        assert result is False


def test_inject_cadl_hook_dry_run():
    """inject_cadl_hook with dry_run=True doesn't modify file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_file = Path(tmpdir) / "SKILL.md"
        original_content = "# Skill\n\nSome content\n"
        skill_file.write_text(original_content)
        
        result = inject_cadl_hook(skill_file, dry_run=True)
        
        assert result is True  # Would inject
        # But file unchanged
        assert skill_file.read_text() == original_content


def test_inject_cadl_hook_no_trailing_newline():
    """inject_cadl_hook handles files without trailing newline"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_file = Path(tmpdir) / "SKILL.md"
        original_content = "# Skill\n\nSome content"  # No trailing newline
        skill_file.write_text(original_content)
        
        inject_cadl_hook(skill_file, dry_run=False)
        
        new_content = skill_file.read_text()
        assert CADL_HOOK in new_content
        # Should have proper newlines
        assert new_content.endswith("\n")


def test_cadl_hook_format():
    """CADL_HOOK constant has correct format"""
    assert "复利资产沉淀机制" in CADL_HOOK
    assert "CADL" in CADL_HOOK
    assert CADL_HOOK.startswith(">")  # Markdown blockquote


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
