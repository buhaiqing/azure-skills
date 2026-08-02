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
    """dry_run mode should not execute az, should return planned."""
    result = run_with_feedback(
        skill="azure-vm-ops",
        operation="vm_create",
        command="az vm create --name test --resource-group test-rg",
        desired_state={"powerState": "VM running"},
        risky=False,
        dry_run=True,
    )
    assert result.status == "planned"
    assert result.trace_id is not None
    assert "dry-run" in result.message.lower() or "planned" in result.message.lower()


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



# ------------------------------------------------------------------
# C-1: Memory store integration tests
# ------------------------------------------------------------------

def test_memory_recommend_reorders_heal_rules():
    """When memory has a successful strategy, it should be ranked first."""
    import tempfile
    from memory.memory_store import MemoryStore
    from auto_feedback_loop import _ranked_heal_rules, _memory_store

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(storage_dir=td)
        # Seed memory: strategy 'b' succeeded 3 times
        for _ in range(3):
            store.record('azure-vm-ops', 'vm_start:powerState', 'b', success=True)
        store.record('azure-vm-ops', 'vm_start:powerState', 'a', success=False)

        # Monkey-patch the global store
        import auto_feedback_loop as afl
        original_store = afl._memory_store
        afl._memory_store = store

        try:
            rules = [
                {'heal_action': 'a', 'args': []},
                {'heal_action': 'b', 'args': []},
                {'heal_action': 'c', 'args': []},
            ]
            ranked = _ranked_heal_rules('azure-vm-ops', 'vm_start:powerState', rules)
            # 'b' should be first (highest success rate)
            assert ranked[0]['heal_action'] == 'b'
            # Rest should follow in original order
            assert [r['heal_action'] for r in ranked] == ['b', 'a', 'c']
        finally:
            afl._memory_store = original_store


def test_memory_miss_uses_default_order():
    """When memory has no data for a symptom, default rule order is preserved."""
    import tempfile
    from memory.memory_store import MemoryStore
    from auto_feedback_loop import _ranked_heal_rules
    import auto_feedback_loop as afl

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(storage_dir=td)
        original_store = afl._memory_store
        afl._memory_store = store

        try:
            rules = [
                {'heal_action': 'x', 'args': []},
                {'heal_action': 'y', 'args': []},
                {'heal_action': 'z', 'args': []},
            ]
            # Symptom not in memory
            ranked = _ranked_heal_rules('azure-vm-ops', 'cold:symptom', rules)
            assert ranked == rules, "Cold start should preserve default order"
        finally:
            afl._memory_store = original_store


def test_record_heal_outcome_persists_to_memory():
    """_record_heal_outcome should persist (skill, symptom, strategy, success) to memory."""
    import tempfile
    from memory.memory_store import MemoryStore
    from auto_feedback_loop import _record_heal_outcome
    import auto_feedback_loop as afl

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(storage_dir=td)
        original_store = afl._memory_store
        afl._memory_store = store

        try:
            # Record a successful heal
            _record_heal_outcome('azure-vm-ops', 'vm_start:powerState', 'restart_vm', True)

            # Verify it was persisted
            rec = store.recommend('azure-vm-ops', 'vm_start:powerState')
            assert rec is not None
            assert rec['strategy'] == 'restart_vm'
            assert rec['success_rate'] == 1.0

            # Record a failed heal
            _record_heal_outcome('azure-vm-ops', 'vm_start:powerState', 'scale_up', False)

            # Verify both are in memory
            rec2 = store.recommend('azure-vm-ops', 'vm_start:powerState')
            assert rec2 is not None
            # 'restart_vm' should still be top (100% success vs 0% for scale_up)
            assert rec2['strategy'] == 'restart_vm'
        finally:
            afl._memory_store = original_store