"""Tests for pattern_miner.py — 异常模式知识库挖掘"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from pattern_miner import write_patterns_to_memory
from memory.memory_store import MemoryStore


def test_write_patterns_to_memory_basic():
    """Test that mined patterns are written to memory store as failure records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)
        
        test_patterns = {
            'patterns': [
                {
                    'skill': 'azure-vm-ops',
                    'operation': 'vm_create',
                    'failure_type': 'heal_exhausted',
                    'recommendation': 'Add healing strategy for azure-vm-ops/vm_create'
                },
                {
                    'skill': 'azure-aks-ops',
                    'operation': 'cluster_create',
                    'failure_type': 'observe_failed',
                    'recommendation': 'Check health_check configuration for azure-aks-ops/cluster_create'
                }
            ]
        }
        
        written = write_patterns_to_memory(test_patterns, storage_dir)
        assert written == 2
        
        store = MemoryStore(storage_dir=storage_dir)
        
        # Verify first pattern
        entries1 = store.recall('azure-vm-ops', 'vm_create:heal_exhausted')
        assert len(entries1) == 1
        assert entries1[0]['success_rate'] == 0.0
        assert 'Add healing strategy' in entries1[0]['strategy']
        
        # Verify second pattern
        entries2 = store.recall('azure-aks-ops', 'cluster_create:observe_failed')
        assert len(entries2) == 1
        assert entries2[0]['success_rate'] == 0.0
        assert 'Check health_check' in entries2[0]['strategy']


def test_write_patterns_to_memory_empty():
    """Test that empty patterns dict writes nothing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)
        
        written = write_patterns_to_memory({'patterns': []}, storage_dir)
        assert written == 0
        
        store = MemoryStore(storage_dir=storage_dir)
        assert len(store.recall('any-skill', 'any-symptom')) == 0


def test_write_patterns_to_memory_truncates_long_recommendation():
    """Test that recommendations longer than 100 chars are truncated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)
        
        long_recommend = 'A' * 150
        test_patterns = {
            'patterns': [
                {
                    'skill': 'azure-vm-ops',
                    'operation': 'vm_create',
                    'failure_type': 'heal_exhausted',
                    'recommendation': long_recommend
                }
            ]
        }
        
        written = write_patterns_to_memory(test_patterns, storage_dir)
        assert written == 1
        
        store = MemoryStore(storage_dir=storage_dir)
        entries = store.recall('azure-vm-ops', 'vm_create:heal_exhausted')
        assert len(entries[0]['strategy']) == 100


def test_write_patterns_to_memory_no_patterns_key():
    """Test that missing 'patterns' key is handled gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)
        
        written = write_patterns_to_memory({}, storage_dir)
        assert written == 0
