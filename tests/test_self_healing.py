"""RED test: self_healing loader should fail until implemented."""
import sys, json
sys.path.insert(0, "scripts")

from self_healing.loader import load_policy, load_registry

def test_load_empty_registry():
    registry = load_registry("scripts/self_healing/registry.json")
    assert registry["version"] == "1.0.0"

def test_load_nonexistent_policy():
    policy = load_policy("azure-nonexistent-ops")
    assert policy is None

def test_load_vm_policy():
    policy = load_policy("azure-vm-ops")
    assert policy is not None
    assert policy["skill"] == "azure-vm-ops"
    assert "operations" in policy
