"""RED test: auto_feedback_loop should fail until implemented."""
import sys
sys.path.insert(0, "scripts")

from dataclasses import dataclass
from auto_feedback_loop import run_with_feedback

@dataclass
class MockArgs:
    skill: str = "azure-vm-ops"
    operation: str = "vm_create"
    command: str = "az vm create --name test --resource-group test-rg"
    desired_state: str = '{"powerState": "VM running"}'
    risky: bool = False
    dry_run: bool = True

def test_dry_run_no_execution():
    """dry_run mode should not execute az, should return status without crashing."""
    result = run_with_feedback(
        skill="azure-vm-ops",
        operation="vm_create",
        command="az vm create --name test --resource-group test-rg",
        desired_state={"powerState": "VM running"},
        risky=False,
        dry_run=True,
    )
    assert result.status in ("success", "escalated", "failed")
    assert result.trace_id is not None

def test_risky_operation_returns_escalated():
    """risky=True operations should return escalated without executing."""
    result = run_with_feedback(
        skill="azure-vm-ops",
        operation="vm_delete",
        command="az vm delete --name myvm --resource-group myrg",
        desired_state={"powerState": "VM running"},
        risky=True,
        dry_run=True,
    )
    assert result.status == "escalated"
    assert "human gate" in result.message.lower() or "risky" in result.message.lower()
