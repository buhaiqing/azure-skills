"""memory/memory_store.py — Execution memory layer for L4 self-healing.

Key-value store keyed on (skill, symptom, strategy) → success rate.
Powers P2-T2: auto-recommend the best repair strategy based on history.

Design:
- One JSONL file per store (append-only write, in-memory aggregate on read)
- stdlib only, zero external dependencies
- Thread-safe for single-process append (JSONL is append-friendly)

API:
    store.record(skill, symptom, strategy, success)
    store.recall(skill, symptom)  → [{"strategy", "success_rate", ...}, ...]
    store.recommend(skill, symptom)  → best entry or None
    store.deprecate(skill, symptom, strategy)
    store.stats()  → {total_entries, unique_skills, unique_symptoms}
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_FILENAME = "memory-store.jsonl"


@dataclass
class MemoryStore:
    """Persistent execution-memory store backed by JSONL."""

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
    # Low-level disk I/O
    # ------------------------------------------------------------------

    def _read_lines(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        text = self._path.read_text(encoding="utf-8").strip()
        if not text:
            return []
        return [json.loads(line) for line in text.splitlines()]

    def _write_lines(self, lines: list[dict[str, Any]]) -> None:
        content = "\n".join(json.dumps(entry, ensure_ascii=False) for entry in lines)
        self._path.write_text(content + "\n", encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(
        self,
        skill: str,
        symptom: str,
        strategy: str,
        success: bool,
    ) -> None:
        """Append one execution record to the store.

        Idempotent by design: each call writes a new line. Repeated
        calls with identical parameters are distinct observations, not
        overwrites.
        """
        entry: dict[str, Any] = {
            "skill": skill,
            "symptom": symptom,
            "strategy": strategy,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        # Append mode: read → add → write back (simple for single-process)
        lines = self._read_lines()
        lines.append(entry)
        self._write_lines(lines)

    def recall(self, skill: str, symptom: str) -> list[dict[str, Any]]:
        """Return all unique strategies for (skill, symptom), sorted by success_rate desc.

        Each returned entry has: strategy, success_rate, count, deprecated (bool).
        Deprecated strategies are included but marked.
        """
        lines = self._read_lines()
        # Filter and aggregate
        bucket: dict[str, dict[str, Any]] = {}
        for entry in lines:
            if entry.get("skill") != skill or entry.get("symptom") != symptom:
                continue
            s = entry["strategy"]
            if s not in bucket:
                bucket[s] = {"total": 0, "successes": 0, "deprecated": False}
            b = bucket[s]
            b["total"] += 1
            if entry.get("success"):
                b["successes"] += 1
            if entry.get("deprecated"):
                b["deprecated"] = True

        results: list[dict[str, Any]] = []
        for strategy, agg in bucket.items():
            rate = agg["successes"] / agg["total"] if agg["total"] > 0 else 0.0
            results.append({
                "strategy": strategy,
                "success_rate": rate,
                "count": agg["total"],
                "deprecated": agg["deprecated"],
            })

        results.sort(key=lambda r: r["success_rate"], reverse=True)
        return results

    def recommend(self, skill: str, symptom: str) -> dict[str, Any] | None:
        """Return the best non-deprecated strategy (highest success_rate), or None."""
        candidates = [
            r for r in self.recall(skill, symptom)
            if not r.get("deprecated")
        ]
        return candidates[0] if candidates else None

    def deprecate(self, skill: str, symptom: str, strategy: str) -> None:
        """Mark all entries for (skill, symptom, strategy) as deprecated.

        No-op if no matching entries exist.
        """
        lines = self._read_lines()
        changed = False
        for entry in lines:
            if (
                entry.get("skill") == skill
                and entry.get("symptom") == symptom
                and entry.get("strategy") == strategy
                and not entry.get("deprecated")  # skip already-deprecated
            ):
                entry["deprecated"] = True
                entry["deprecated_at"] = datetime.now(timezone.utc).isoformat()
                changed = True
        if changed:
            self._write_lines(lines)

    def stats(self) -> dict[str, int]:
        """Return aggregate counts for the entire store."""
        lines = self._read_lines()
        skills: set[str] = set()
        symptoms: set[str] = set()
        for entry in lines:
            skills.add(entry.get("skill", ""))
            symptoms.add(entry.get("symptom", ""))
        skills.discard("")
        symptoms.discard("")
        return {
            "total_entries": len(lines),
            "unique_skills": len(skills),
            "unique_symptoms": len(symptoms),
        }

    def prune(self) -> int:
        """Prune stale entries: mark as deprecated any strategy that:

        1. Has not been used (no new records) in > 30 days, OR
        2. Has success_rate < 0.5 (based on all entries for that strategy)

        Returns: number of strategies newly deprecated this call.
        """
        lines = self._read_lines()
        if not lines:
            return 0

        # Build aggregation by (skill, symptom, strategy)
        groups: dict[tuple[str, str, str], dict[str, Any]] = {}
        for entry in lines:
            skill = entry.get("skill", "")
            symptom = entry.get("symptom", "")
            strategy = entry.get("strategy", "")
            key = (skill, symptom, strategy)
            if key not in groups:
                groups[key] = {"total": 0, "successes": 0, "deprecated": False, "latest_ts": ""}
            g = groups[key]
            g["total"] += 1
            if entry.get("success"):
                g["successes"] += 1
            if entry.get("deprecated"):
                g["deprecated"] = True
            ts = entry.get("timestamp", "")
            if ts > g["latest_ts"]:
                g["latest_ts"] = ts

        now = datetime.now(timezone.utc)
        newly_deprecated: set[tuple[str, str, str]] = set()

        for key, g in groups.items():
            if g["deprecated"]:
                continue  # skip already deprecated

            skill, symptom, strategy = key

            # Condition 1: stale — > 30 days since last record
            if g["latest_ts"]:
                try:
                    last_used = datetime.fromisoformat(g["latest_ts"])
                except ValueError:
                    last_used = datetime.min.replace(tzinfo=timezone.utc)
                if (now - last_used).days > 30:
                    self.deprecate(skill, symptom, strategy)
                    newly_deprecated.add(key)
                    continue

            # Condition 2: low success rate — < 50%
            rate = g["successes"] / g["total"] if g["total"] > 0 else 0.0
            if rate < 0.5:
                self.deprecate(skill, symptom, strategy)
                newly_deprecated.add(key)

        return len(newly_deprecated)

    def transfer(
        self,
        knowledge: str,
        source_skill: str,
        target_skill: str,
        symptom_mapping: dict[str, str] | None = None,
    ) -> int:
        """Transfer experiences from source_skill to target_skill.

        Copies all non-deprecated strategies from source_skill's recall
        for the given knowledge (symptom) to target_skill.

        Args:
            knowledge: The symptom/knowledge to transfer
            source_skill: Source skill name
            target_skill: Target skill name
            symptom_mapping: Optional mapping of source symptom -> target symptom.
                             If None, uses the same symptom name.

        Returns: number of strategy records created.
        """
        source_results = self.recall(source_skill, knowledge)
        created = 0
        for entry in source_results:
            if entry.get("deprecated"):
                continue
            target_symptom = knowledge
            if symptom_mapping and knowledge in symptom_mapping:
                target_symptom = symptom_mapping[knowledge]
            self.record(target_skill, target_symptom, entry["strategy"], success=True)
            created += 1
        return created
