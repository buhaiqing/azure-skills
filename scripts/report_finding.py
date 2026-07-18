#!/usr/bin/env python3
"""
report_finding.py — CADL findings 写入

将异常模式写入 .runtime/findings/<date>-<id8>.json
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


RUNTIME_DIR = Path(__file__).parent.parent / ".runtime"
FINDINGS_DIR = RUNTIME_DIR / "findings"


def report_finding(
    skill: str,
    operation: str,
    failure_type: str,  # "heal_exhausted" | "observe_failed" | "command_failed"
    context: dict,
    trace_id: Optional[str] = None,
) -> Path:
    """
    将异常模式写入 .runtime/findings/<date>-<id8>.json。
    供 CADL 后续提取、归因、沉淀为可复用资产。
    """
    os.makedirs(FINDINGS_DIR, exist_ok=True)
    short_id = str(uuid.uuid4())[:8]
    finding = {
        "id": short_id,
        "date": datetime.now(timezone.utc).isoformat(),
        "skill": skill,
        "operation": operation,
        "failure_type": failure_type,
        "context": context,
        "trace_id": trace_id,
        "cadl_trigger": True,
    }
    path = FINDINGS_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}-{short_id}.json"
    path.write_text(json.dumps(finding, indent=2, ensure_ascii=False))
    return path
