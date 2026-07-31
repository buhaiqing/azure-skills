#!/usr/bin/env python3
"""Risk tier resolver — R0 / R1 / R2 for MS L400 governance."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

TIERS_PATH = Path(__file__).resolve().parent / "risk_tiers.json"


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    return json.loads(TIERS_PATH.read_text(encoding="utf-8"))


def resolve_tier(skill: str, operation: str) -> str:
    """Return R0 | R1 | R2 for skill/operation."""
    data = _load()
    overrides = data.get("operation_overrides", {}).get(skill, {})
    if operation in overrides:
        return overrides[operation]
    op_l = operation.lower()
    for rule in data.get("default_by_keyword", []):
        if re.search(rule["pattern"], op_l, re.I):
            return rule["tier"]
    return "R1"


def tier_policy(tier: str) -> dict[str, Any]:
    data = _load()
    return dict(data["tiers"].get(tier, data["tiers"]["R1"]))


def apply_tier_gates(
    skill: str,
    operation: str,
    *,
    risky_flag: bool = False,
) -> dict[str, Any]:
    """Compute effective gates for auto_feedback_loop / GCL.

    Returns dict with keys: tier, auto_heal, human_confirm, max_heal_attempts,
    gcl_required, force_risky (treat as human-gate).
    """
    tier = resolve_tier(skill, operation)
    pol = tier_policy(tier)
    force_risky = bool(pol.get("human_confirm")) or risky_flag or tier == "R2"
    return {
        "tier": tier,
        "auto_heal": bool(pol.get("auto_heal")) and not force_risky,
        "human_confirm": force_risky,
        "max_heal_attempts": 0 if force_risky else int(pol.get("max_heal_attempts", 2)),
        "gcl_required": bool(pol.get("gcl_required")),
        "gcl_max_iter": int(pol.get("gcl_max_iter", 2)),
        "force_risky": force_risky,
    }


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--skill", required=True)
    p.add_argument("--operation", required=True)
    args = p.parse_args()
    print(json.dumps(apply_tier_gates(args.skill, args.operation), indent=2))
