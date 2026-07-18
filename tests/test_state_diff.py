"""RED test: state_diff should fail until implemented."""
import sys
sys.path.insert(0, "scripts")

from state_diff import diff, DiffResult

def test_diff_equal_states():
    desired = {"status": "running", "powerState": "VM running"}
    actual  = {"status": "running", "powerState": "VM running"}
    result = diff(desired, actual, "vm_create")
    assert result.match is True
    assert result.diffs == []

def test_diff_mismatch():
    desired = {"powerState": "VM running"}
    actual  = {"powerState": "VM deallocated"}
    result = diff(desired, actual, "vm_create")
    assert result.match is False
    assert len(result.diffs) == 1
    assert result.diffs[0].field == "powerState"

def test_diff_missing_field():
    desired = {"provisioningState": "Succeeded"}
    actual  = {}
    result = diff(desired, actual, "vm_create")
    assert result.match is False

def test_diff_nested_list_access():
    """JMESPath-like [n].field access"""
    actual = {"statuses": [None, {"displayStatus": "VM running"}]}
    desired = {"statuses[1].displayStatus": "VM running"}
    result = diff(desired, actual, "vm_create")
    assert result.match is True
