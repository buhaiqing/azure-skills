#!/usr/bin/env python3
"""
orchestrator.py — Cross-skill BFS diagnostic engine for Azure Services.

Detects service dependency chains, builds diagnosis paths, and suggests
healing actions in topological order.

Usage:
    python scripts/orchestrator.py --list-deps <skill_name>
    python scripts/orchestrator.py --diagnose <symptom_or_skill>
    python scripts/orchestrator.py --list-rca
    python scripts/orchestrator.py --heal <skill_name> <symptom>
"""

import json
import os
import sys
from collections import deque
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEP_GRAPH_PATH = REPO_ROOT / "scripts" / "dependency_graph.json"
RUNTIME_PATTERNS_DIR = REPO_ROOT / ".runtime" / "cross_skill_patterns"


# ============================================================
# Dependency graph loader
# ============================================================

def _load_graph() -> dict[str, Any]:
    """Load the dependency graph from JSON."""
    if not DEP_GRAPH_PATH.exists():
        print(f"[ERROR] Dependency graph not found at {DEP_GRAPH_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(DEP_GRAPH_PATH) as f:
        return json.load(f)


def _build_adjacency(graph: dict) -> dict[str, list[str]]:
    """Build forward adjacency: skill → [its direct deps]."""
    return {name: node["direct_deps"] for name, node in graph["nodes"].items()}


# ============================================================
# BFS dependency chain
# ============================================================

def bfs_deps(skill: str, graph: dict, max_depth: int = 3) -> list[str]:
    """BFS traversal from a skill, returning dependency chain in topological order.

    BFS ensures we diagnose foundation services first (shallow deps).
    max_depth limits chain length to avoid unbounded recursion.
    """
    adj = _build_adjacency(graph)
    if skill not in adj:
        return []

    visited: set[str] = set()
    chain: list[str] = []
    queue: deque[tuple[str, int]] = deque()
    queue.append((skill, 0))

    while queue:
        node, depth = queue.popleft()
        if node in visited or depth > max_depth:
            continue
        visited.add(node)
        if node != skill:
            chain.append(node)
        for dep in adj.get(node, []):
            if dep not in visited:
                queue.append((dep, depth + 1))

    return chain


def reverse_deps(skill: str, graph: dict) -> list[str]:
    """Find all services that depend on this skill (reverse dependency)."""
    adj = _build_adjacency(graph)
    reverse: list[str] = []
    for name, deps in adj.items():
        if skill in deps:
            reverse.append(name)
    return reverse


# ============================================================
# RCA path matching
# ============================================================

def match_rca_path(symptom: str, graph: dict) -> list[dict] | None:
    """Match a symptom description to predefined RCA paths (fuzzy match)."""
    symptom_lower = symptom.lower()
    matches: list[dict] = []
    for path in graph.get("rca_paths", []):
        # Match on symptom keywords
        path_symptom = path["symptom"].lower()
        keywords = path_symptom.replace(",", "").split()
        match_count = sum(1 for kw in keywords if kw in symptom_lower)
        if match_count > 0:
            matches.append({
                "id": path["id"],
                "symptom": path["symptom"],
                "diagnosis_chain": path["diagnosis_chain"],
                "description": path["description"],
                "match_score": match_count / len(keywords),
            })

    if not matches:
        return None

    # Sort by match score descending
    matches.sort(key=lambda m: m["match_score"], reverse=True)
    return matches


# ============================================================
# Cross-skill healing order
# ============================================================

def healing_order(skill: str, graph: dict) -> list[str]:
    """Return the order in which skills should be healed.

    Foundation services first (deps), then the target skill.
    This prevents fixing a symptom while the root cause is still broken.
    """
    dep_chain = bfs_deps(skill, graph)
    # Reverse: heal deepest dependency first, then work up to the target
    healing = list(reversed(dep_chain))
    if skill not in healing:
        healing.append(skill)
    return healing


# ============================================================
# CADL pattern persistence
# ============================================================

def _ensure_patterns_dir() -> None:
    RUNTIME_PATTERNS_DIR.mkdir(parents=True, exist_ok=True)


def persist_cross_skill_pattern(skill: str, symptom: str, diagnosis_chain: list[str],
                                 success: bool) -> dict:
    """Save a discovered cross-skill diagnosis pattern for future reuse.

    Patterns are stored in .runtime/cross_skill_patterns/ as JSONL files.
    """
    _ensure_patterns_dir()
    pattern_file = RUNTIME_PATTERNS_DIR / f"{skill}.jsonl"

    entry = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "skill": skill,
        "symptom": symptom,
        "diagnosis_chain": diagnosis_chain,
        "success": success,
    }

    with open(pattern_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def list_cross_skill_patterns(skill: str | None = None) -> list[dict]:
    """Read back persisted cross-skill patterns."""
    _ensure_patterns_dir()
    patterns: list[dict] = []
    pattern_files = list(RUNTIME_PATTERNS_DIR.glob("*.jsonl"))

    for pf in pattern_files:
        if skill and pf.stem != skill:
            continue
        with open(pf) as f:
            for line in f:
                line = line.strip()
                if line:
                    patterns.append(json.loads(line))
    return patterns


# ============================================================
# CLI
# ============================================================

def _print_chain(chain: list[str], graph: dict) -> None:
    """Pretty-print a diagnosis/healing chain."""
    if not chain:
        print("  (no dependencies)")
        return
    for i, step in enumerate(chain):
        node = graph["nodes"].get(step, {})
        service = node.get("service", step)
        svc_type = node.get("type", "unknown")
        print(f"  {i+1}. {step} ({service}) — type={svc_type}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/orchestrator.py --list-deps <skill_name>")
        print("  python scripts/orchestrator.py --diagnose <symptom_or_skill>")
        print("  python scripts/orchestrator.py --list-rca")
        print("  python scripts/orchestrator.py --heal <skill_name> <symptom>")
        print("  python scripts/orchestrator.py --list-patterns [skill_name]")
        sys.exit(1)

    command = sys.argv[1]
    graph = _load_graph()

    if command == "--list-deps":
        if len(sys.argv) < 3:
            print("Usage: --list-deps <skill_name>")
            sys.exit(1)
        skill = sys.argv[2]
        deps = bfs_deps(skill, graph)
        rev_deps = reverse_deps(skill, graph)
        print(f"Dependencies for {skill}:")
        _print_chain(deps, graph)
        print(f"\nServices depending on {skill}:")
        if rev_deps:
            for r in rev_deps:
                node = graph["nodes"].get(r, {})
                print(f"  {r} ({node.get('service', '')})")
        else:
            print("  (none)")

    elif command == "--diagnose":
        symptom = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not symptom:
            print("Usage: --diagnose <symptom_or_skill>")
            sys.exit(1)

        # Try RCA path matching first
        rca_matches = match_rca_path(symptom, graph)
        if rca_matches:
            best = rca_matches[0]
            print(f"Matched RCA path: {best['id']} (score={best['match_score']:.0%})")
            print(f"Symptom: {best['symptom']}")
            print(f"Diagnosis chain:")
            _print_chain(best["diagnosis_chain"], graph)
            print(f"\nDescription: {best['description']}")
            # Persist pattern
            persist_cross_skill_pattern(
                best["diagnosis_chain"][0] if best["diagnosis_chain"] else "unknown",
                symptom, best["diagnosis_chain"], True,
            )
        else:
            # Fallback: treat as skill name
            skill = symptom.replace(" ", "-").lower()
            skill_name = skill if skill.startswith("azure-") else f"azure-{skill}"
            if skill_name in graph["nodes"]:
                deps = bfs_deps(skill_name, graph)
                print(f"Skill '{skill_name}' found. Dependencies:")
                _print_chain(deps, graph)
            else:
                print(f"No RCA match for '{symptom}' and no skill named '{skill_name}' found.")
                print("\nAvailable RCA paths:")
                for path in graph.get("rca_paths", []):
                    print(f"  {path['id']}: {path['symptom']}")

    elif command == "--list-rca":
        print("Available RCA paths:")
        for path in graph.get("rca_paths", []):
            print(f"\n  {path['id']}: {path['symptom']}")
            print(f"  Chain: {' → '.join(path['diagnosis_chain'])}")
            print(f"  {path['description']}")

    elif command == "--heal":
        if len(sys.argv) < 4:
            print("Usage: --heal <skill_name> <symptom>")
            sys.exit(1)
        skill = sys.argv[2]
        symptom = " ".join(sys.argv[3:])
        order = healing_order(skill, graph)
        print(f"Healing order for {skill} (foundation first):")
        _print_chain(order, graph)
        persist_cross_skill_pattern(skill, symptom, order, True)

    elif command == "--list-patterns":
        skill = sys.argv[2] if len(sys.argv) > 2 else None
        patterns = list_cross_skill_patterns(skill)
        if patterns:
            print(f"Cross-skill patterns ({len(patterns)} entries):")
            for p in patterns:
                status = "✓" if p.get("success") else "✗"
                chain = " → ".join(p.get("diagnosis_chain", []))
                print(f"  [{status}] {p.get('skill')}: {p.get('symptom')} → {chain}")
        else:
            print("No cross-skill patterns recorded yet.")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
