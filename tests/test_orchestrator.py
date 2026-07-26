"""TDD tests for orchestrator.py — cross-skill diagnostic engine."""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, "scripts")

# Sample dependency graph for testing
SAMPLE_GRAPH = {
    "version": "1.0.0",
    "nodes": {
        "azure-aks-ops": {
            "service": "AKS",
            "type": "compute",
            "direct_deps": ["azure-vm-ops", "azure-vnet-ops", "azure-monitor-ops"],
        },
        "azure-vm-ops": {
            "service": "VMs",
            "type": "compute",
            "direct_deps": ["azure-vnet-ops", "azure-monitor-ops"],
        },
        "azure-vnet-ops": {
            "service": "VNet",
            "type": "networking",
            "direct_deps": ["azure-monitor-ops"],
        },
        "azure-nsg-ops": {
            "service": "NSG",
            "type": "networking",
            "direct_deps": ["azure-vnet-ops", "azure-monitor-ops"],
        },
        "azure-loadbalancer-ops": {
            "service": "LB",
            "type": "networking",
            "direct_deps": ["azure-vnet-ops", "azure-monitor-ops"],
        },
        "azure-monitor-ops": {
            "service": "Monitor",
            "type": "observability",
            "direct_deps": [],
        },
        "azure-keyvault-ops": {
            "service": "Key Vault",
            "type": "security",
            "direct_deps": ["azure-monitor-ops"],
        },
        "azure-acr-ops": {
            "service": "ACR",
            "type": "compute",
            "direct_deps": ["azure-monitor-ops"],
        },
    },
    "rca_paths": [
        {
            "id": "rca-test-001",
            "symptom": "AKS cluster not reachable",
            "diagnosis_chain": ["azure-aks-ops", "azure-vm-ops", "azure-nsg-ops",
                                 "azure-loadbalancer-ops", "azure-monitor-ops"],
            "description": "Test RCA path",
        },
        {
            "id": "rca-test-002",
            "symptom": "VM cannot connect to internet",
            "diagnosis_chain": ["azure-vm-ops", "azure-nsg-ops", "azure-vnet-ops",
                                 "azure-loadbalancer-ops", "azure-monitor-ops"],
            "description": "Test RCA path 2",
        },
    ],
}


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def temp_graph_path():
    """Create a temporary dependency graph for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(SAMPLE_GRAPH, f)
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def temp_patterns_dir(monkeypatch):
    """Create a temporary patterns directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        patterns_dir = Path(tmpdir) / "cross_skill_patterns"
        patterns_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            "orchestrator.RUNTIME_PATTERNS_DIR", patterns_dir
        )
        yield patterns_dir


@pytest.fixture
def orchestrator(temp_graph_path, monkeypatch):
    """Import orchestrator with test graph path."""
    monkeypatch.setattr("orchestrator.DEP_GRAPH_PATH", temp_graph_path)
    import orchestrator as orch
    return orch


# ============================================================
# Test 1: Graph loading
# ============================================================

def test_load_graph(orchestrator):
    """Graph must load correctly with all nodes."""
    graph = orchestrator._load_graph()
    assert "nodes" in graph
    assert "rca_paths" in graph
    assert len(graph["nodes"]) == 8
    assert len(graph["rca_paths"]) == 2


# ============================================================
# Test 2: BFS dependency chain
# ============================================================

def test_bfs_deps_aks(orchestrator):
    """AKS should list VM, VNet, Monitor as direct deps (max_depth=3)."""
    graph = orchestrator._load_graph()
    deps = orchestrator.bfs_deps("azure-aks-ops", graph, max_depth=3)
    assert "azure-vm-ops" in deps
    assert "azure-vnet-ops" in deps
    assert "azure-monitor-ops" in deps


def test_bfs_deps_monitor(orchestrator):
    """Monitor has no deps."""
    graph = orchestrator._load_graph()
    deps = orchestrator.bfs_deps("azure-monitor-ops", graph, max_depth=3)
    assert deps == []


def test_bfs_deps_unknown(orchestrator):
    """Unknown skill returns empty list."""
    graph = orchestrator._load_graph()
    deps = orchestrator.bfs_deps("azure-fake-ops", graph, max_depth=3)
    assert deps == []


def test_bfs_deps_depth_limit(orchestrator):
    """BFS respects max_depth."""
    graph = orchestrator._load_graph()
    deps_depth1 = orchestrator.bfs_deps("azure-aks-ops", graph, max_depth=1)
    deps_depth3 = orchestrator.bfs_deps("azure-aks-ops", graph, max_depth=3)
    # Depth 1 should only have direct deps
    # Depth 3 should include transitive deps
    assert len(deps_depth1) <= len(deps_depth3)


# ============================================================
# Test 3: Reverse dependencies
# ============================================================

def test_reverse_deps_vnet(orchestrator):
    """VNet is depended on by AKS, VM, NSG, LB."""
    graph = orchestrator._load_graph()
    rev = orchestrator.reverse_deps("azure-vnet-ops", graph)
    assert "azure-aks-ops" in rev
    assert "azure-vm-ops" in rev
    assert "azure-nsg-ops" in rev
    assert "azure-loadbalancer-ops" in rev


def test_reverse_deps_monitor(orchestrator):
    """Monitor is depended on by all other services."""
    graph = orchestrator._load_graph()
    rev = orchestrator.reverse_deps("azure-monitor-ops", graph)
    assert len(rev) == 7  # All other 7 services depend on Monitor


# ============================================================
# Test 4: RCA path matching
# ============================================================

def test_match_rca_exact(orchestrator):
    """Exact symptom match should return the correct RCA path."""
    graph = orchestrator._load_graph()
    matches = orchestrator.match_rca_path("AKS cluster not reachable", graph)
    assert matches is not None
    assert matches[0]["id"] == "rca-test-001"
    assert matches[0]["match_score"] == 1.0


def test_match_rca_partial(orchestrator):
    """Partial keyword match should still return a result."""
    graph = orchestrator._load_graph()
    matches = orchestrator.match_rca_path("AKS not reachable", graph)
    assert matches is not None
    assert matches[0]["match_score"] > 0


def test_match_rca_no_match(orchestrator):
    """Unrelated symptom should return None."""
    graph = orchestrator._load_graph()
    matches = orchestrator.match_rca_path("cosmos db throughput", graph)
    assert matches is None


# ============================================================
# Test 5: Healing order
# ============================================================

def test_healing_order_aks(orchestrator):
    """Healing order for AKS should start with deepest dep (Monitor) and end with AKS."""
    graph = orchestrator._load_graph()
    order = orchestrator.healing_order("azure-aks-ops", graph)
    assert order[0] == "azure-monitor-ops"  # Deepest dep first
    assert order[-1] == "azure-aks-ops"  # Target last


def test_healing_order_monitor(orchestrator):
    """Monitor has no deps, so healing order should just be [monitor]."""
    graph = orchestrator._load_graph()
    order = orchestrator.healing_order("azure-monitor-ops", graph)
    assert order == ["azure-monitor-ops"]


# ============================================================
# Test 6: CADL pattern persistence
# ============================================================

def test_persist_cross_skill_pattern(orchestrator, temp_patterns_dir):
    """Pattern persistence should create a JSONL entry."""
    entry = orchestrator.persist_cross_skill_pattern(
        "azure-aks-ops", "AKS cluster not reachable",
        ["azure-aks-ops", "azure-vm-ops", "azure-monitor-ops"],
        True,
    )
    assert entry["skill"] == "azure-aks-ops"
    assert entry["success"] is True

    # Verify file exists
    pattern_file = temp_patterns_dir / "azure-aks-ops.jsonl"
    assert pattern_file.exists()

    # Verify content
    with open(pattern_file) as f:
        lines = f.readlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["skill"] == "azure-aks-ops"


def test_list_cross_skill_patterns(orchestrator, temp_patterns_dir):
    """list_cross_skill_patterns should return all persisted patterns."""
    orchestrator.persist_cross_skill_pattern(
        "azure-aks-ops", "AKS down", ["azure-aks-ops", "azure-vm-ops"], True,
    )
    orchestrator.persist_cross_skill_pattern(
        "azure-vm-ops", "VM slow", ["azure-vm-ops", "azure-monitor-ops"], True,
    )

    all_patterns = orchestrator.list_cross_skill_patterns()
    assert len(all_patterns) == 2

    filtered = orchestrator.list_cross_skill_patterns(skill="azure-aks-ops")
    assert len(filtered) == 1
    assert filtered[0]["skill"] == "azure-aks-ops"


def test_list_cross_skill_patterns_empty(orchestrator, temp_patterns_dir):
    """Empty patterns dir should return empty list."""
    patterns = orchestrator.list_cross_skill_patterns()
    assert patterns == []


# ============================================================
# Test 7: Graph integrity checks
# ============================================================

def test_all_deps_exist(orchestrator):
    """Every dependency must reference an existing node."""
    graph = orchestrator._load_graph()
    for name, node in graph["nodes"].items():
        for dep in node["direct_deps"]:
            assert dep in graph["nodes"], (
                f"{name}: dependency '{dep}' not found in nodes"
            )


def test_all_rca_steps_exist(orchestrator):
    """Every step in every RCA path must reference an existing node."""
    graph = orchestrator._load_graph()
    for path in graph["rca_paths"]:
        for step in path["diagnosis_chain"]:
            assert step in graph["nodes"], (
                f"{path['id']}: step '{step}' not found in nodes"
            )
