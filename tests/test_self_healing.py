"""RED test: self_healing loader should fail until implemented."""
import sys, json
sys.path.insert(0, "scripts")

from self_healing.loader import load_policy, load_registry

def test_load_empty_registry():
    registry = load_registry("scripts/self_healing/registry.json")
    assert registry["version"].startswith("1.")

def test_load_nonexistent_policy():
    policy = load_policy("azure-nonexistent-ops")
    assert policy is None

def test_load_vm_policy():
    policy = load_policy("azure-vm-ops")
    assert policy is not None
    assert policy["skill"] == "azure-vm-ops"
    assert "operations" in policy

def test_load_appgateway_policy():
    policy = load_policy("azure-appgateway-ops")
    assert policy is not None
    assert policy["skill"] == "azure-appgateway-ops"
    assert "operations" in policy
    assert "appgateway_create" in policy["operations"]
    assert policy["operations"]["appgateway_create"]["risky"] is False
    assert policy["operations"]["appgateway_delete"]["risky"] is True

def test_load_loadbalancer_policy():
    policy = load_policy("azure-loadbalancer-ops")
    assert policy is not None
    assert policy["skill"] == "azure-loadbalancer-ops"
    assert "operations" in policy
    assert policy["operations"]["lb_create"]["risky"] is False
    assert policy["operations"]["lb_delete"]["risky"] is True

def test_load_frontdoor_policy():
    policy = load_policy("azure-frontdoor-ops")
    assert policy is not None
    assert policy["skill"] == "azure-frontdoor-ops"
    assert "operations" in policy
    assert policy["operations"]["frontdoor_create"]["risky"] is False

def test_validate_all_policies():
    """validate.py reports all 6 policy files valid"""
    import subprocess
    r = subprocess.run(
        ["python3", "scripts/self_healing/validate.py"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "All policy files valid" in r.stdout
