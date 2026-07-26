"""P2-T2.1: TDD tests for scripts/memory/memory_store.py

Execution memory layer for L4 self-healing.
Key-value store keyed on (skill, symptom, strategy) → success rate.
stdlib-only, JSON-file persistent, zero external dependencies.

contract from roadmap:
  record(skill, symptom, strategy, success) → persist
  recall(skill, symptom) → ranked strategies by success_rate
  recommend(skill, symptom) → best strategy or None
  deprecate(skill, symptom, strategy) → mark as deprecated
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "scripts")

# ------------------------------------------------------------------
# Test 1–4: Record (CREATE)
# ------------------------------------------------------------------

def test_memory_store_module_importable():
    """Module `scripts/memory/memory_store.py` must exist and be importable."""
    try:
        from memory import memory_store  # noqa: F401
    except ImportError:
        pytest.fail("memory/memory_store module is not yet created")


def test_record_new_entry(tmp_path):
    """record() must accept a new (skill, symptom, strategy) tuple and persist it."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    store.record(
        skill="azure-vm-ops",
        symptom="statuses[1].displayStatus != VM running",
        strategy="az vm start",
        success=True,
    )

    # Read back from disk to confirm persistence
    entries = [json.loads(line) for line in store._path.read_text().strip().splitlines() if line]
    assert len(entries) == 1
    assert entries[0]["skill"] == "azure-vm-ops"
    assert entries[0]["symptom"] == "statuses[1].displayStatus != VM running"
    assert entries[0]["strategy"] == "az vm start"
    assert entries[0]["success"] is True
    assert "timestamp" in entries[0]


def test_record_multiple_entries(tmp_path):
    """Multiple record() calls must all be persisted and have unique timestamps."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    for i in range(5):
        store.record("azure-aks-ops", "NodeNotReady", "az aks nodepool upgrade", i % 2 == 0)

    entries = [json.loads(line) for line in store._path.read_text().strip().splitlines() if line]
    assert len(entries) == 5
    # All timestamps unique
    timestamps = [e["timestamp"] for e in entries]
    assert len(set(timestamps)) == 5


def test_record_idempotent(tmp_path):
    """Recording the same entry twice adds two lines, not overwriting."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    store.record("azure-vm-ops", "powerState != running", "az vm start", True)
    store.record("azure-vm-ops", "powerState != running", "az vm start", False)

    entries = [json.loads(line) for line in store._path.read_text().strip().splitlines() if line]
    assert len(entries) == 2, "should append, not overwrite"


# ------------------------------------------------------------------
# Test 5–8: Recall (READ)
# ------------------------------------------------------------------

def test_recall_returns_all_strategies(tmp_path):
    """recall(skill, symptom) must return all recorded strategies for that pair."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    store.record("azure-vm-ops", "powerState", "az vm restart", True)
    store.record("azure-vm-ops", "powerState", "az vm restart", False)

    results = store.recall("azure-vm-ops", "powerState")
    # Each unique strategy should appear once in recall
    strategy_names = [r["strategy"] for r in results]
    assert "az vm start" in strategy_names
    assert "az vm restart" in strategy_names


def test_recall_no_match_returns_empty(tmp_path):
    """recall() for an unknown skill/symptom returns empty list, not error."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    results = store.recall("azure-never-seen-ops", "unknown_symptom")
    assert results == [], f"expected [], got {results}"


def test_recall_calculates_success_rate(tmp_path):
    """recall() must attach a success_rate (0.0–1.0) to each strategy."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    # 3 successes, 1 failure → rate = 0.75
    for _ in range(3):
        store.record("azure-vm-ops", "powerState", "az vm start", True)
    store.record("azure-vm-ops", "powerState", "az vm start", False)

    results = store.recall("azure-vm-ops", "powerState")
    start_entry = [r for r in results if r["strategy"] == "az vm start"][0]
    assert "success_rate" in start_entry
    assert start_entry["success_rate"] == 0.75


def test_recall_sorts_by_success_rate_desc(tmp_path):
    """recall() results must be sorted by success_rate descending."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    # Strategy A: 100% success
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    # Strategy B: 50% success
    store.record("azure-vm-ops", "powerState", "az vm restart", True)
    store.record("azure-vm-ops", "powerState", "az vm restart", False)

    results = store.recall("azure-vm-ops", "powerState")
    rates = [r["success_rate"] for r in results]
    assert rates == sorted(rates, reverse=True), f"Not sorted desc: {rates}"


# ------------------------------------------------------------------
# Test 9–11: Recommend (best strategy)
# ------------------------------------------------------------------

def test_recommend_returns_best_strategy(tmp_path):
    """recommend(skill, symptom) must return the highest-success-rate strategy."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    store.record("azure-vm-ops", "powerState", "az vm restart", True)
    store.record("azure-vm-ops", "powerState", "az vm restart", False)

    rec = store.recommend("azure-vm-ops", "powerState")
    assert rec is not None
    assert rec["strategy"] == "az vm start"  # 100% > 50%


def test_recommend_no_history_returns_none(tmp_path):
    """recommend() for unknown skill/symptom returns None."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    assert store.recommend("azure-blobstorage-ops", "no_history") is None


def test_recommend_excludes_deprecated(tmp_path):
    """recommend() must skip deprecated strategies."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    store.record("azure-vm-ops", "powerState", "az vm restart", False)
    store.record("azure-vm-ops", "powerState", "az vm restart", False)

    store.deprecate("azure-vm-ops", "powerState", "az vm restart")
    rec = store.recommend("azure-vm-ops", "powerState")
    assert rec["strategy"] == "az vm start", "should skip deprecated restart"


# ------------------------------------------------------------------
# Test 12–14: Deprecate (UPDATE)
# ------------------------------------------------------------------

def test_deprecate_adds_deprecated_flag(tmp_path):
    """deprecate() must update entries on disk to set deprecated=True."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    store.record("azure-aks-ops", "NodeNotReady", "az aks nodepool upgrade", True)
    store.record("azure-aks-ops", "NodeNotReady", "az aks nodepool upgrade", True)
    store.record("azure-aks-ops", "NodeNotReady", "az aks delete", False)
    store.record("azure-aks-ops", "NodeNotReady", "az aks delete", False)

    store.deprecate("azure-aks-ops", "NodeNotReady", "az aks delete")

    results = store.recall("azure-aks-ops", "NodeNotReady")
    delete_entry = [r for r in results if r["strategy"] == "az aks delete"][0]
    assert delete_entry.get("deprecated") is True


def test_deprecate_nonexistent_no_error(tmp_path):
    """deprecate() on unknown entry must NOT raise or crash."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    store.deprecate("azure-nonexistent-ops", "no_symptom", "no_strategy")
    # No exception, no crash — just a no-op


def test_deprecate_is_persisted(tmp_path):
    """After deprecate() + re-opening store, deprecated flag must persist."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    store.record("azure-vm-ops", "powerState", "az vm restart", True)
    store.deprecate("azure-vm-ops", "powerState", "az vm restart")

    # Re-open store from same directory
    store2 = MemoryStore(storage_dir=tmp_path)
    results = store2.recall("azure-vm-ops", "powerState")
    assert results[0]["deprecated"] is True


# ------------------------------------------------------------------
# Test 15–16: Stats / Summary
# ------------------------------------------------------------------

def test_stats_returns_counts(tmp_path):
    """stats() must return total entries, unique skills, unique symptoms."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    store.record("azure-aks-ops", "NodeNotReady", "az aks upgrade", False)

    s = store.stats()
    assert s["total_entries"] == 3
    assert s["unique_skills"] == 2
    assert s["unique_symptoms"] == 2


def test_stats_empty_store(tmp_path):
    """stats() on empty store must return zeros, not error."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    s = store.stats()
    assert s["total_entries"] == 0


# ------------------------------------------------------------------
# Test 17-20: Prune (Memory Decay)
# ------------------------------------------------------------------

def test_prune_deprecates_low_success_rate(tmp_path):
    """prune() must deprecate strategies with < 50% success rate."""
    from memory.memory_store import MemoryStore
    store = MemoryStore(storage_dir=tmp_path)
    # 3 failures, 1 success → 25% rate
    store.record("azure-vm-ops", "powerState", "az vm restart", False)
    store.record("azure-vm-ops", "powerState", "az vm restart", False)
    store.record("azure-vm-ops", "powerState", "az vm restart", False)
    store.record("azure-vm-ops", "powerState", "az vm restart", True)

    n = store.prune()
    assert n >= 1, "should deprecate low-success strategy"

    rec = store.recommend("azure-vm-ops", "powerState")
    assert rec is None or rec["strategy"] != "az vm restart", \
        "low-success strategy should not be recommended"


def test_prune_deprecates_stale_entries(monkeypatch, tmp_path):
    """prune() must deprecate strategies not used in > 30 days."""
    from memory.memory_store import MemoryStore
    from datetime import datetime, timezone, timedelta

    store = MemoryStore(storage_dir=tmp_path)
    store.record("azure-vm-ops", "powerState", "az vm start", True)

    # Manually rewrite timestamp to be 40 days ago
    lines = store._read_lines()
    old_ts = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    for line in lines:
        line["timestamp"] = old_ts
    store._write_lines(lines)

    n = store.prune()
    assert n >= 1, "should deprecate stale strategy"


def test_prune_skips_healthy_strategies(tmp_path):
    """prune() must NOT deprecate strategies with > 50% rate and recent usage."""
    from memory.memory_store import MemoryStore

    store = MemoryStore(storage_dir=tmp_path)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    store.record("azure-vm-ops", "powerState", "az vm start", True)

    n = store.prune()
    assert n == 0, "should not deprecate healthy strategy"

    rec = store.recommend("azure-vm-ops", "powerState")
    assert rec is not None
    assert rec["strategy"] == "az vm start"


def test_prune_empty_store(tmp_path):
    """prune() on empty store returns 0, not error."""
    from memory.memory_store import MemoryStore
    store = MemoryStore(storage_dir=tmp_path)
    assert store.prune() == 0


# ------------------------------------------------------------------
# Test 21-24: Transfer (Cross-skill Knowledge Sharing)
# ------------------------------------------------------------------

def test_transfer_copies_strategies(tmp_path):
    """transfer() must copy strategies from source to target skill."""
    from memory.memory_store import MemoryStore
    
    store = MemoryStore(storage_dir=tmp_path)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    store.record("azure-vm-ops", "powerState", "az vm restart", True)
    
    n = store.transfer("powerState", "azure-vm-ops", "azure-aks-ops")
    assert n == 2, f"expected 2 strategies transferred, got {n}"
    
    target_results = store.recall("azure-aks-ops", "powerState")
    assert len(target_results) == 2
    strategies = {r["strategy"] for r in target_results}
    assert strategies == {"az vm start", "az vm restart"}


def test_transfer_skips_deprecated(tmp_path):
    """transfer() must NOT copy deprecated strategies."""
    from memory.memory_store import MemoryStore
    
    store = MemoryStore(storage_dir=tmp_path)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    store.record("azure-vm-ops", "powerState", "az vm restart", False)
    store.deprecate("azure-vm-ops", "powerState", "az vm restart")
    
    n = store.transfer("powerState", "azure-vm-ops", "azure-aks-ops")
    assert n == 1, f"expected only 1 (non-deprecated), got {n}"
    
    target_results = store.recall("azure-aks-ops", "powerState")
    assert len(target_results) == 1
    assert target_results[0]["strategy"] == "az vm start"


def test_transfer_with_symptom_mapping(tmp_path):
    """transfer() must support symptom_mapping parameter."""
    from memory.memory_store import MemoryStore
    
    store = MemoryStore(storage_dir=tmp_path)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    
    n = store.transfer(
        "powerState", "azure-vm-ops", "azure-aks-ops",
        symptom_mapping={"powerState": "nodePowerState"}
    )
    assert n == 1
    
    # Should be recorded under mapped symptom
    results_old = store.recall("azure-aks-ops", "powerState")
    assert len(results_old) == 0, "should not be under old symptom name"
    
    results_new = store.recall("azure-aks-ops", "nodePowerState")
    assert len(results_new) == 1


def test_transfer_no_source_returns_zero(tmp_path):
    """transfer() with no source data returns 0, not error."""
    from memory.memory_store import MemoryStore
    
    store = MemoryStore(storage_dir=tmp_path)
    n = store.transfer("unknown_symptom", "azure-vm-ops", "azure-aks-ops")
    assert n == 0


def test_transfer_creates_new_records_not_overwrites(tmp_path):
    """transfer() must append new records, not overwrite existing ones."""
    from memory.memory_store import MemoryStore
    
    store = MemoryStore(storage_dir=tmp_path)
    store.record("azure-vm-ops", "powerState", "az vm start", True)
    
    # Transfer twice
    store.transfer("powerState", "azure-vm-ops", "azure-aks-ops")
    store.transfer("powerState", "azure-vm-ops", "azure-aks-ops")
    
    target_results = store.recall("azure-aks-ops", "powerState")
    assert len(target_results) == 1, "same strategy should not duplicate in recall"
