"""Tests for self_healing.loader auto-discovery (C-2)"""
import json
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from self_healing.loader import (
    discover_policies,
    load_registry,
    rebuild_registry,
    load_policy,
)


def test_discover_policies_empty_dir():
    """discover_policies returns empty dict when directory is empty"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = discover_policies(tmpdir)
        assert result == {}


def test_discover_policies_finds_heal_files():
    """discover_policies finds all *_heal.json files and maps correctly"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test heal files
        (Path(tmpdir) / "vm_heal.json").write_text("{}")
        (Path(tmpdir) / "aks_heal.json").write_text("{}")
        (Path(tmpdir) / "blobstorage_heal.json").write_text("{}")
        # Non-heal file should be ignored
        (Path(tmpdir) / "other.json").write_text("{}")
        
        result = discover_policies(tmpdir)
        
        assert len(result) == 3
        assert result["azure-vm-ops"] == "vm_heal.json"
        assert result["azure-aks-ops"] == "aks_heal.json"
        assert result["azure-blobstorage-ops"] == "blobstorage_heal.json"


def test_discover_policies_naming_convention():
    """discover_policies follows naming convention: {short}_heal.json → azure-{short}-ops"""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "test_heal.json").write_text("{}")
        
        result = discover_policies(tmpdir)
        
        assert "azure-test-ops" in result
        assert result["azure-test-ops"] == "test_heal.json"


def test_rebuild_registry_creates_new():
    """rebuild_registry creates registry.json when it doesn't exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test heal files
        (Path(tmpdir) / "vm_heal.json").write_text("{}")
        (Path(tmpdir) / "aks_heal.json").write_text("{}")
        
        reg_path = Path(tmpdir) / "registry.json"
        
        result = rebuild_registry(tmpdir, reg_path)
        
        assert reg_path.exists()
        assert "skills" in result
        assert result["skills"]["azure-vm-ops"] == "vm_heal.json"
        assert result["skills"]["azure-aks-ops"] == "aks_heal.json"


def test_rebuild_registry_preserves_existing():
    """rebuild_registry preserves existing entries and adds new ones"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create existing registry
        reg_path = Path(tmpdir) / "registry.json"
        existing = {
            "version": "1.0.0",
            "metadata": {"author": "test"},
            "skills": {"azure-old-ops": "old_heal.json"}
        }
        reg_path.write_text(json.dumps(existing))
        
        # Create new heal files
        (Path(tmpdir) / "vm_heal.json").write_text("{}")
        (Path(tmpdir) / "aks_heal.json").write_text("{}")
        
        result = rebuild_registry(tmpdir, reg_path)
        
        # Should preserve metadata
        assert result["version"] == "1.0.0"
        assert result["metadata"]["author"] == "test"
        # Should preserve old skill
        assert result["skills"]["azure-old-ops"] == "old_heal.json"
        # Should add new skills
        assert result["skills"]["azure-vm-ops"] == "vm_heal.json"
        assert result["skills"]["azure-aks-ops"] == "aks_heal.json"


def test_rebuild_registry_updates_existing_mapping():
    """rebuild_registry updates filename if skill already exists with different file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create existing registry with old filename
        reg_path = Path(tmpdir) / "registry.json"
        existing = {
            "skills": {"azure-vm-ops": "vm_old_heal.json"}
        }
        reg_path.write_text(json.dumps(existing))
        
        # Create new heal file with standard name
        (Path(tmpdir) / "vm_heal.json").write_text("{}")
        
        result = rebuild_registry(tmpdir, reg_path)
        
        # Should update to new filename
        assert result["skills"]["azure-vm-ops"] == "vm_heal.json"


def test_load_policy_with_renamed_blobstorage():
    """load_policy works with blobstorage_heal.json (renamed from blob_heal.json)"""
    # This test uses the actual registry.json in the repo
    policy = load_policy("azure-blobstorage-ops")
    
    # Should load successfully (file exists and is valid JSON)
    assert policy is not None
    assert isinstance(policy, dict)


def test_discover_policies_real_directory():
    """discover_policies works with actual self_healing directory"""
    # Use the real policy directory
    from self_healing.loader import POLICY_DIR
    
    result = discover_policies(POLICY_DIR)
    
    # Should find all 31 policies
    assert len(result) == 31
    # Should include key skills
    assert "azure-vm-ops" in result
    assert "azure-aks-ops" in result
    assert "azure-blobstorage-ops" in result
    # All values should end with _heal.json
    for filename in result.values():
        assert filename.endswith("_heal.json")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
