"""TDD tests for scripts/tasks.py — L4 Roadmap Task Tracker.

Manages L4 implementation tasks: definition, state machine, dependency
checking, and progress calculation.

contract:
  TaskTracker.add_task(task_id, title, phase, deps) → append to registry
  TaskTracker.start(task_id) → pending → in_progress
  TaskTracker.complete(task_id) → in_progress → completed
  TaskTracker.block(task_id, reason) → in_progress → blocked
  TaskTracker.unblock(task_id) → blocked → pending
  TaskTracker.progress() → per-phase completion stats
  TaskTracker.is_blocked(task_id) → True if blocked by pending deps
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "scripts")


# ------------------------------------------------------------------
# Test 1-3: Module & Registry
# ------------------------------------------------------------------

def test_tasks_module_importable():
    """Module `scripts/tasks.py` must exist and be importable."""
    try:
        import tasks  # noqa: F401
    except ImportError:
        pytest.fail("tasks module is not yet created")


def test_add_task(tmp_path):
    """add_task() must accept a task definition and persist it."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    tracker.add_task(
        task_id="P1-T1.1",
        title="Design llm_critic.py architecture",
        phase="Phase 1",
        depends_on=[],
    )

    tasks_list = tracker.list_all()
    assert len(tasks_list) == 1
    assert tasks_list[0]["id"] == "P1-T1.1"
    assert tasks_list[0]["title"] == "Design llm_critic.py architecture"
    assert tasks_list[0]["phase"] == "Phase 1"
    assert tasks_list[0]["status"] == "pending"


def test_add_duplicate_task_raises(tmp_path):
    """Adding a task with an existing ID must raise ValueError."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    tracker.add_task("P1-T1.1", "Design llm_critic.py", "Phase 1", [])
    with pytest.raises(ValueError, match="already exists"):
        tracker.add_task("P1-T1.1", "Duplicate", "Phase 1", [])


# ------------------------------------------------------------------
# Test 4-7: State Machine
# ------------------------------------------------------------------

def test_start_task(tmp_path):
    """start() must transition pending → in_progress and record started_at."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    tracker.add_task("P1-T1.1", "Design llm_critic.py", "Phase 1", [])
    tracker.start("P1-T1.1")

    t = tracker.get("P1-T1.1")
    assert t["status"] == "in_progress"
    assert "started_at" in t


def test_complete_task(tmp_path):
    """complete() must transition in_progress → completed and record completed_at."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    tracker.add_task("P1-T1.1", "Design llm_critic.py", "Phase 1", [])
    tracker.start("P1-T1.1")
    tracker.complete("P1-T1.1")

    t = tracker.get("P1-T1.1")
    assert t["status"] == "completed"
    assert "completed_at" in t


def test_block_and_unblock_task(tmp_path):
    """block() must transition in_progress → blocked. unblock() → pending."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    tracker.add_task("P1-T1.1", "Design llm_critic.py", "Phase 1", [])
    tracker.start("P1-T1.1")
    tracker.block("P1-T1.1", "Waiting for LLM API access")

    t = tracker.get("P1-T1.1")
    assert t["status"] == "blocked"
    assert t["block_reason"] == "Waiting for LLM API access"

    tracker.unblock("P1-T1.1")
    t = tracker.get("P1-T1.1")
    assert t["status"] == "pending"


def test_invalid_state_transition_raises(tmp_path):
    """Calling complete() on a pending task must raise ValueError."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    tracker.add_task("P1-T1.1", "Design llm_critic.py", "Phase 1", [])
    # Not started → cannot complete
    with pytest.raises(ValueError, match="Cannot complete task"):
        tracker.complete("P1-T1.1")

    # Already completed → cannot start again
    tracker.start("P1-T1.1")
    tracker.complete("P1-T1.1")
    with pytest.raises(ValueError, match="Cannot start task"):
        tracker.start("P1-T1.1")


# ------------------------------------------------------------------
# Test 8-11: Dependency Management
# ------------------------------------------------------------------

def test_is_blocked_by_deps(tmp_path):
    """is_blocked() must return True if any dependency is not completed."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    tracker.add_task("P1-T1.1", "Design llm_critic.py", "Phase 1", [])
    tracker.add_task("P1-T1.2", "Fallback scenarios", "Phase 1", ["P1-T1.1"])

    # P1-T1.1 is pending → P1-T1.2 is blocked
    assert tracker.is_blocked("P1-T1.2") is True

    # Complete P1-T1.1 → P1-T1.2 unblocked
    tracker.start("P1-T1.1")
    tracker.complete("P1-T1.1")
    assert tracker.is_blocked("P1-T1.2") is False


def test_is_blocked_no_deps(tmp_path):
    """is_blocked() on a task with no deps returns False."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    tracker.add_task("P1-T1.1", "Design llm_critic.py", "Phase 1", [])
    assert tracker.is_blocked("P1-T1.1") is False


def test_multi_level_deps(tmp_path):
    """A → B → C: B blocked until A done; C blocked until B done."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    tracker.add_task("A", "Task A", "Phase 1", [])
    tracker.add_task("B", "Task B", "Phase 1", ["A"])
    tracker.add_task("C", "Task C", "Phase 1", ["B"])

    assert tracker.is_blocked("B") is True
    assert tracker.is_blocked("C") is True

    tracker.start("A")
    tracker.complete("A")
    assert tracker.is_blocked("B") is False
    assert tracker.is_blocked("C") is True  # B still not done

    tracker.start("B")
    tracker.complete("B")
    assert tracker.is_blocked("C") is False


def test_dep_cycle_detection(tmp_path):
    """Setting A → B when B → A already exists must raise ValueError."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    tracker.add_task("A", "Task A", "Phase 1", [])
    tracker.add_task("B", "Task B", "Phase 1", ["A"])

    # Setting A's deps to include B creates A → B, but B → A already
    with pytest.raises(ValueError, match="dependency cycle"):
        tracker.update_deps("A", ["B"])


def test_add_task_self_dep_raises(tmp_path):
    """Adding a task that depends on itself must raise ValueError."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    with pytest.raises(ValueError, match="self-dependency"):
        tracker.add_task("A", "Task A", "Phase 1", ["A"])


# ------------------------------------------------------------------
# Test 12-14: Progress Calculation
# ------------------------------------------------------------------

def test_progress_per_phase(tmp_path):
    """progress() must return per-phase completion percentages."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    # Phase 1: 2 tasks, 1 completed
    tracker.add_task("P1-T1", "Task 1", "Phase 1", [])
    tracker.add_task("P1-T2", "Task 2", "Phase 1", [])
    tracker.start("P1-T1")
    tracker.complete("P1-T1")

    # Phase 2: 1 task, 0 completed
    tracker.add_task("P2-T1", "Task 3", "Phase 2", [])
    tracker.start("P2-T1")  # in_progress but not completed

    prog = tracker.progress()
    assert "Phase 1" in prog
    assert prog["Phase 1"]["total"] == 2
    assert prog["Phase 1"]["completed"] == 1
    assert prog["Phase 1"]["pct"] == 50.0

    assert "Phase 2" in prog
    assert prog["Phase 2"]["total"] == 1
    assert prog["Phase 2"]["completed"] == 0
    assert prog["Phase 2"]["pct"] == 0.0


def test_progress_overall(tmp_path):
    """progress() overall field must aggregate all phases."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    tracker.add_task("A", "Task A", "Phase 1", [])
    tracker.add_task("B", "Task B", "Phase 2", [])

    tracker.start("A")
    tracker.complete("A")

    prog = tracker.progress()
    assert prog["overall"]["total"] == 2
    assert prog["overall"]["completed"] == 1
    assert prog["overall"]["pct"] == 50.0


def test_progress_empty(tmp_path):
    """progress() on empty tracker returns zeros, not error."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    prog = tracker.progress()
    assert prog["overall"]["total"] == 0
    assert prog["overall"]["completed"] == 0
    assert prog["overall"]["pct"] == 0.0


# ------------------------------------------------------------------
# Test 15-16: Persistence
# ------------------------------------------------------------------

def test_persistence_across_instances(tmp_path):
    """Tasks must persist across different TaskTracker instances."""
    from tasks import TaskTracker

    t1 = TaskTracker(storage_dir=tmp_path)
    t1.add_task("P1-T1.1", "Design llm_critic.py", "Phase 1", [])
    t1.start("P1-T1.1")

    t2 = TaskTracker(storage_dir=tmp_path)
    task = t2.get("P1-T1.1")
    assert task["id"] == "P1-T1.1"
    assert task["status"] == "in_progress"


def test_export_json(tmp_path):
    """export() must serialize all tasks to JSON-serializable dict."""
    from tasks import TaskTracker

    tracker = TaskTracker(storage_dir=tmp_path)
    tracker.add_task("A", "Task A", "Phase 1", [])
    tracker.start("A")
    tracker.complete("A")

    exported = tracker.export()
    assert "tasks" in exported
    assert len(exported["tasks"]) == 1
    assert exported["tasks"]["A"]["id"] == "A"
    assert exported["tasks"]["A"]["status"] == "completed"

    # Must be JSON-serializable
    json_str = json.dumps(exported, ensure_ascii=False)
    assert json.loads(json_str) == exported