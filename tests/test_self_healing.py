"""RED test: self_healing loader should fail until implemented."""
import sys, json
sys.path.insert(0, "scripts")

from self_healing.loader import load_policy, load_registry

def test_load_empty_registry():
    registry = load_registry("scripts/self_healing/registry.json")
    assert registry["version"] == "2.0.0"

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
    """validate.py reports all 31 policy files valid"""
    import subprocess
    r = subprocess.run(
        ["python3", "scripts/self_healing/validate.py"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "All policy files valid" in r.stdout


def test_all_31_policies_load():
    """每个策略文件都能正确加载，skill名匹配，operations非空"""
    registry = load_registry("scripts/self_healing/registry.json")
    skills = list(registry["skills"].keys())
    assert len(skills) == 31, f"expected 31 skills, got {len(skills)}"
    for skill in skills:
        policy = load_policy(skill)
        assert policy is not None, f"{skill}: load_policy returned None"
        assert policy["skill"] == skill, f"{skill}: skill name mismatch {policy['skill']}"
        assert "operations" in policy, f"{skill}: missing operations"
        assert len(policy["operations"]) > 0, f"{skill}: empty operations"
        # 每个 operation 必须有 risky 字段
        for op_name, op_config in policy["operations"].items():
            assert "risky" in op_config, f"{skill}.{op_name}: missing risky field"
