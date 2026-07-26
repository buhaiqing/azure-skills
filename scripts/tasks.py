"""tasks.py — L4 Roadmap Task Tracker.

Manages L4 implementation tasks with state machine, dependency checking,
and progress calculation.

Design:
- JSON file persistence (stdlib only, zero external deps)
- Full state machine: pending → in_progress → completed
  - blocked: in_progress → blocked → pending (unblock)
- Dependency graph: add_task with cycle detection on update_deps
- Progress: per-phase and overall completion percentages

API:
    tracker.add_task(task_id, title, phase, depends_on)
    tracker.start(task_id)
    tracker.complete(task_id)
    tracker.block(task_id, reason)
    tracker.unblock(task_id)
    tracker.is_blocked(task_id) → bool
    tracker.progress() → per-phase + overall stats
    tracker.export() → JSON-serializable dict
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_FILENAME = "tasks.json"

VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"in_progress"},
    "in_progress": {"completed", "blocked"},
    "blocked": {"pending"},  # unblock → back to pending
    "completed": set(),      # terminal state
}


@dataclass
class TaskTracker:
    """Persistent task tracker for L4 roadmap implementation."""

    storage_dir: Path
    filename: str = DEFAULT_FILENAME

    def __post_init__(self) -> None:
        if isinstance(self.storage_dir, str):
            self.storage_dir = Path(self.storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @property
    def _path(self) -> Path:
        return self.storage_dir / self.filename

    # ------------------------------------------------------------------
    # Disk I/O
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        """Load the full tasks registry from disk."""
        if not self._path.exists():
            return {"tasks": {}}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self, registry: dict[str, Any]) -> None:
        """Persist the registry atomically (write-then-rename for safety)."""
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.rename(self._path)

    def _get_entry(self, task_id: str) -> dict[str, Any]:
        reg = self._load()
        if task_id not in reg["tasks"]:
            raise KeyError(f"Task '{task_id}' not found")
        return reg["tasks"][task_id]

    def _update_entry(self, task_id: str, updates: dict[str, Any]) -> None:
        reg = self._load()
        if task_id not in reg["tasks"]:
            raise KeyError(f"Task '{task_id}' not found")
        reg["tasks"][task_id].update(updates)
        self._save(reg)

    # ------------------------------------------------------------------
    # Core API: CRUD
    # ------------------------------------------------------------------

    def add_task(
        self,
        task_id: str,
        title: str,
        phase: str,
        depends_on: list[str],
    ) -> None:
        """Add a new task to the registry."""
        reg = self._load()
        if task_id in reg["tasks"]:
            raise ValueError(f"Task '{task_id}' already exists")

        if task_id in set(depends_on):
            raise ValueError(
                f"self-dependency: task '{task_id}' cannot depend on itself"
            )

        entry: dict[str, Any] = {
            "id": task_id,
            "title": title,
            "phase": phase,
            "status": "pending",
            "depends_on": sorted(set(depends_on)),
            "block_reason": None,
            "started_at": None,
            "completed_at": None,
        }
        reg["tasks"][task_id] = entry
        self._save(reg)

    def get(self, task_id: str) -> dict[str, Any]:
        """Return a single task entry (deep-copied so caller can't mutate)."""
        return deepcopy(self._get_entry(task_id))

    def list_all(self) -> list[dict[str, Any]]:
        """Return all tasks as a list."""
        reg = self._load()
        return deepcopy([t for t in reg["tasks"].values()])

    def export(self) -> dict[str, Any]:
        """Export the full registry as a JSON-serializable dict."""
        return self._load()

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def _transition(self, task_id: str, target: str) -> None:
        """Low-level: transition task to target state (validation already done)."""
        reg = self._load()
        reg["tasks"][task_id]["status"] = target
        self._save(reg)

    def _check_transition(self, task_id: str, target: str) -> None:
        """Validate that task_id can transition from current → target."""
        entry = self._get_entry(task_id)
        current = entry["status"]
        allowed = VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(
                f"Cannot {_verb_for(target)} task '{task_id}': "
                f"current status is '{current}'"
            )

    def start(self, task_id: str) -> None:
        """Transition pending → in_progress. Records started_at timestamp."""
        self._check_transition(task_id, "in_progress")
        self._update_entry(task_id, {
            "status": "in_progress",
            "started_at": datetime.now(timezone.utc).isoformat(),
        })

    def complete(self, task_id: str) -> None:
        """Transition in_progress → completed. Records completed_at timestamp."""
        self._check_transition(task_id, "completed")
        self._update_entry(task_id, {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

    def block(self, task_id: str, reason: str) -> None:
        """Transition in_progress → blocked. Stores block reason."""
        self._check_transition(task_id, "blocked")
        self._update_entry(task_id, {
            "status": "blocked",
            "block_reason": reason,
        })

    def unblock(self, task_id: str) -> None:
        """Transition blocked → pending. Clears block reason."""
        self._check_transition(task_id, "pending")
        self._update_entry(task_id, {
            "status": "pending",
            "block_reason": None,
        })

    # ------------------------------------------------------------------
    # Dependency management
    # ------------------------------------------------------------------

    def is_blocked(self, task_id: str) -> bool:
        """Check if task is blocked by incomplete dependencies."""
        entry = self._get_entry(task_id)
        deps = entry.get("depends_on", [])
        if not deps:
            return False
        reg = self._load()
        for dep_id in deps:
            dep_entry = reg["tasks"].get(dep_id)
            if dep_entry is None or dep_entry["status"] != "completed":
                return True
        return False

    def _detect_cycle(self, start: str, target_deps: set[str]) -> bool:
        """DFS from target_deps: if we can reach start, it's a cycle."""
        reg = self._load()
        visited: set[str] = set()
        stack = list(target_deps)
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            if node == start:
                return True
            visited.add(node)
            entry = reg["tasks"].get(node)
            if entry:
                stack.extend(entry.get("depends_on", []))
        return False

    def update_deps(self, task_id: str, new_deps: list[str]) -> None:
        """Update a task's dependencies. Raises on cycle detection."""
        new_dep_set = set(new_deps)
        if self._detect_cycle(task_id, new_dep_set):
            raise ValueError(
                f"dependency cycle: setting {task_id} → {new_deps} "
                f"would create a cycle"
            )
        self._update_entry(task_id, {"depends_on": sorted(new_dep_set)})

    # ------------------------------------------------------------------
    # Progress calculation
    # ------------------------------------------------------------------

    def progress(self) -> dict[str, Any]:
        """Return per-phase and overall completion stats."""
        reg = self._load()
        tasks = list(reg["tasks"].values())

        phases: dict[str, dict[str, int]] = {}
        for t in tasks:
            phase = t["phase"]
            if phase not in phases:
                phases[phase] = {"total": 0, "completed": 0}
            phases[phase]["total"] += 1
            if t["status"] == "completed":
                phases[phase]["completed"] += 1

        result: dict[str, Any] = {}
        total_all = 0
        completed_all = 0
        for phase, counts in sorted(phases.items()):
            pct = (counts["completed"] / counts["total"] * 100) if counts["total"] > 0 else 0.0
            result[phase] = {
                "total": counts["total"],
                "completed": counts["completed"],
                "pct": round(pct, 1),
            }
            total_all += counts["total"]
            completed_all += counts["completed"]

        overall_pct = (completed_all / total_all * 100) if total_all > 0 else 0.0
        result["overall"] = {
            "total": total_all,
            "completed": completed_all,
            "pct": round(overall_pct, 1),
        }
        return result


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _verb_for(state: str) -> str:
    """Human-readable verb for state transitions."""
    return {
        "completed": "complete",
        "in_progress": "start",
        "blocked": "block",
        "pending": "unblock",
    }.get(state, f"transition to {state}")
