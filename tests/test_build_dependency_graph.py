"""Tests for build_dependency_graph.py (C-4)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from build_dependency_graph import (
    extract_short_name,
    infer_service_type,
    infer_dependencies,
    scan_skills,
    build_dependency_graph,
)


def test_extract_short_name():
    """extract_short_name removes azure- prefix and -ops suffix"""
    assert extract_short_name("azure-vm-ops") == "vm"
    assert extract_short_name("azure-aks-ops") == "aks"
    assert extract_short_name("azure-blobstorage-ops") == "blobstorage"
    assert extract_short_name("azure-appgateway-ops") == "appgateway"


def test_infer_service_type():
    """infer_service_type maps short names to service categories"""
    assert infer_service_type("vm") == "compute"
    assert infer_service_type("aks") == "compute"
    assert infer_service_type("vnet") == "networking"
    assert infer_service_type("loadbalancer") == "networking"
    assert infer_service_type("blobstorage") == "storage"
    assert infer_service_type("sqldb") == "database"
    assert infer_service_type("servicebus") == "messaging"
    assert infer_service_type("keyvault") == "identity"
    assert infer_service_type("monitor") == "observability"
    # Unknown type
    assert infer_service_type("unknown") == "unknown"


def test_infer_dependencies_compute():
    """infer_dependencies returns correct deps for compute services"""
    deps = infer_dependencies("azure-vm-ops", "compute")
    assert "azure-vnet-ops" in deps
    assert "azure-nsg-ops" in deps
    assert "azure-monitor-ops" in deps
    
    # AKS has additional deps
    aks_deps = infer_dependencies("azure-aks-ops", "compute")
    assert "azure-loadbalancer-ops" in aks_deps
    assert "azure-acr-ops" in aks_deps
    assert "azure-keyvault-ops" in aks_deps


def test_infer_dependencies_networking():
    """infer_dependencies returns correct deps for networking services"""
    deps = infer_dependencies("azure-vnet-ops", "networking")
    assert "azure-monitor-ops" in deps
    assert "azure-nsg-ops" in deps  # VNet depends on NSG
    
    # Front Door has additional deps
    fd_deps = infer_dependencies("azure-frontdoor-ops", "networking")
    assert "azure-dns-ops" in fd_deps
    assert "azure-trafficmanager-ops" in fd_deps


def test_infer_dependencies_storage():
    """infer_dependencies returns correct deps for storage services"""
    deps = infer_dependencies("azure-blobstorage-ops", "storage")
    assert "azure-monitor-ops" in deps
    assert "azure-keyvault-ops" in deps
    
    # Backup has site-recovery dep
    backup_deps = infer_dependencies("azure-backup-ops", "storage")
    assert "azure-site-recovery-ops" in backup_deps


def test_infer_dependencies_database():
    """infer_dependencies returns correct deps for database services"""
    deps = infer_dependencies("azure-sqldb-ops", "database")
    assert "azure-vnet-ops" in deps
    assert "azure-nsg-ops" in deps
    assert "azure-monitor-ops" in deps
    assert "azure-keyvault-ops" in deps


def test_infer_dependencies_unknown():
    """infer_dependencies returns default deps for unknown type"""
    deps = infer_dependencies("azure-unknown-ops", "unknown")
    assert deps == ["azure-monitor-ops"]


def test_scan_skills():
    """scan_skills finds all azure-*-ops directories"""
    repo_root = Path(__file__).parent.parent
    skills = scan_skills(repo_root)
    
    assert len(skills) == 31
    # Check structure
    for skill in skills:
        assert "name" in skill
        assert "short_name" in skill
        assert "service_type" in skill
        assert "service_name" in skill
        assert "description" in skill
        assert "dependencies" in skill
        assert skill["name"].startswith("azure-")
        assert skill["name"].endswith("-ops")


def test_build_dependency_graph_structure():
    """build_dependency_graph returns correct structure"""
    repo_root = Path(__file__).parent.parent
    skills = scan_skills(repo_root)
    graph = build_dependency_graph(skills)
    
    assert "version" in graph
    assert "description" in graph
    assert "nodes" in graph
    assert "rca_paths" in graph
    assert len(graph["nodes"]) == 31


def test_build_dependency_graph_node_structure():
    """Each node in dependency graph has required fields"""
    repo_root = Path(__file__).parent.parent
    skills = scan_skills(repo_root)
    graph = build_dependency_graph(skills)
    
    for skill_name, node in graph["nodes"].items():
        assert "service" in node
        assert "type" in node
        assert "direct_deps" in node
        assert "description" in node
        assert isinstance(node["direct_deps"], list)
        # Self-dependency check
        assert skill_name not in node["direct_deps"]


def test_build_dependency_graph_key_skills():
    """Key skills are present with correct dependencies"""
    repo_root = Path(__file__).parent.parent
    skills = scan_skills(repo_root)
    graph = build_dependency_graph(skills)
    
    # AKS should have many deps (vnet, nsg, monitor, loadbalancer, acr, keyvault)
    aks_node = graph["nodes"]["azure-aks-ops"]
    assert len(aks_node["direct_deps"]) >= 5
    assert "azure-vnet-ops" in aks_node["direct_deps"]
    assert "azure-acr-ops" in aks_node["direct_deps"]
    
    # VM should have networking deps
    vm_node = graph["nodes"]["azure-vm-ops"]
    assert "azure-vnet-ops" in vm_node["direct_deps"]
    assert "azure-nsg-ops" in vm_node["direct_deps"]


def test_no_orphan_nodes():
    """All skills should be in the graph (no orphans)"""
    repo_root = Path(__file__).parent.parent
    skills = scan_skills(repo_root)
    graph = build_dependency_graph(skills)
    
    skill_names = {skill["name"] for skill in skills}
    graph_nodes = set(graph["nodes"].keys())
    
    assert skill_names == graph_nodes


def test_no_circular_dependencies():
    """Dependency graph should not have circular dependencies"""
    repo_root = Path(__file__).parent.parent
    skills = scan_skills(repo_root)
    graph = build_dependency_graph(skills)
    
    # Simple check: no skill should depend on itself
    for skill_name, node in graph["nodes"].items():
        assert skill_name not in node["direct_deps"], f"{skill_name} depends on itself"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
