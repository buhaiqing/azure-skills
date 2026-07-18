#!/usr/bin/env python3
"""
az_trace.py — Lightweight auto-tracer for Azure CLI

Drop-in wrapper that intercepts `az` commands, scores them against the GCL rubric,
and persists normalized traces to audit-results/.

Usage (replace `az` with this script in any skill execution):
    python scripts/az_trace.py run "az vm show --name my-vm --resource-group my-rg --output json"

    # With explicit skill (auto-detected if omitted):
    python scripts/az_trace.py run --skill azure-vm-ops "az vm delete ..."

    # Destructive operations are flagged automatically.
    # Credentials are masked in traces (***).

No dependencies beyond stdlib. Python >= 3.10.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# --- Constants ---

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = REPO_ROOT / "audit-results"
TRACE_PREFIX = "gcl-trace"
TIMESTAMP_FMT = "%Y%m%d-%H%M%S"

# Skills where GCL is REQUIRED (destructive operations need explicit confirmation)
GCL_REQUIRED_SKILLS = frozenset({
    "azure-vm-ops", "azure-aks-ops", "azure-blobstorage-ops",
    "azure-appgateway-ops", "azure-loadbalancer-ops", "azure-frontdoor-ops",
    "azure-trafficmanager-ops", "azure-backup-ops", "azure-dns-ops",
    "azure-file-storage-ops", "azure-queue-storage-ops", "azure-site-recovery-ops",
    "azure-eventgrid-ops", "azure-apim-ops",
})

# Destructive operation keywords (case-insensitive)
DESTRUCTIVE_PATTERNS = re.compile(
    r"\b(delete|terminate|destroy|purge|remove|stop\s+--?\s*deallocate|"
    r"deallocate|drop\s+table|drop\s+database|reset|purge\s+key|"
    r"scale\s+-+\s*0|node-count\s+0|--yes\s+-\s*y|--force-deletion)\b",
    re.IGNORECASE,
)

# Credential patterns to mask in traces
CREDENTIAL_PATTERNS = re.compile(
    r"(AZURE_CLIENT_SECRET|AZURE_|subscription[_-]?id|tenant[_-]?id|"
    r"client[_-]?id|client[_-]?secret|access[_-]?key|connection[_-]?string|"
    r"password|token|Bearer\s+[a-zA-Z0-9._-]+)",
    re.IGNORECASE,
)

# Map az subcommand prefixes to skill names
AZ_TO_SKILL = {
    "vm": "azure-vm-ops",
    "aks": "azure-aks-ops",
    "storage account": "azure-blobstorage-ops",
    "storage container": "azure-blobstorage-ops",
    "storage blob": "azure-blobstorage-ops",
    "storage share": "azure-file-storage-ops",
    "storage queue": "azure-queue-storage-ops",
    "network application-gateway": "azure-appgateway-ops",
    "network lb": "azure-loadbalancer-ops",
    "afd": "azure-frontdoor-ops",
    "network traffic-manager": "azure-trafficmanager-ops",
    "backup": "azure-backup-ops",
    "site-recovery": "azure-site-recovery-ops",
    "network dns": "azure-dns-ops",
    "eventhubs": "azure-eventhub-ops",
    "eventgrid": "azure-eventgrid-ops",
    "servicebus": "azure-servicebus-ops",
    "functionapp": "azure-function-ops",
    "webapp": "azure-appservice-ops",
    "containerapp": "azure-aci-ops",
    "containerreg": "azure-acr-ops",
    "cosmosdb": "azure-cosmos-ops",
    "sql": "azure-sqldb-ops",
    "postgres": "azure-postgres-ops",
    "redis": "azure-redis-ops",
    "keyvault": "azure-keyvault-ops",
    "monitor": "azure-monitor-ops",
    "policy": "azure-audit-ops",
    "role": "azure-audit-ops",
    "lock": "azure-audit-ops",
    "group": "azure-vnet-ops",
    "network vnet": "azure-vnet-ops",
    "network nsg": "azure-nsg-ops",
    "network private-endpoint": "azure-privateendpoint-ops",
    "apim": "azure-apim-ops",
}


# --- Data Models ---

@dataclass
class GeneratorResult:
    command: str
    args: dict
    exit_code: int
    stdout: str
    stderr: str
    elapsed_sec: float


@dataclass
class CriticScores:
    correctness: float
    safety: float
    idempotency: float
    traceability: float
    spec_compliance: float


@dataclass
class CriticResult:
    scores: CriticScores
    suggestions: list[str]
    blocking: bool


@dataclass
class Iteration:
    iter: int
    generator: GeneratorResult
    critic: CriticResult
    decision: str


@dataclass
class GCLTrace:
    skill: str
    request: str
    rubric_version: str
    iterations: list[Iteration] = field(default_factory=list)
    final: Optional[dict] = None


# --- Helpers ---

def ts() -> str:
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FMT)


def mask_credentials(text: str) -> str:
    """Replace credential values with *** in traces."""
    return CREDENTIAL_PATTERNS.sub("***", text)


def is_destructive(command: str) -> bool:
    return bool(DESTRUCTIVE_PATTERNS.search(command))


def detect_skill(command: str) -> str:
    """Infer skill from az subcommand."""
    lower = command.lower()
    for pattern, skill in AZ_TO_SKILL.items():
        if pattern in lower:
            return skill
    return "unknown"


def default_rubric(skill: str, is_destructive: bool) -> dict:
    """Return per-skill rubric thresholds."""
    required = skill in GCL_REQUIRED_SKILLS
    safety_threshold = 1.0 if (required or is_destructive) else 0.5
    return {
        "correctness": {"scale": [0, 0.5, 1], "threshold": 0.5},
        "safety": {"scale": [0, 1], "threshold": safety_threshold},
        "idempotency": {"scale": [0, 0.5, 1], "threshold": 0.5},
        "traceability": {"scale": [0, 0.5, 1], "threshold": 0.5},
        "spec_compliance": {"scale": [0, 0.5, 1], "threshold": 0.5},
    }


def parse_args(command: str) -> dict:
    """Parse az command string into a dict of flags and values."""
    parts = command.split()
    args = {}
    i = 0
    while i < len(parts):
        p = parts[i]
        if p.startswith("--"):
            key = p[2:].replace("-", "_")
            if i + 1 < len(parts) and not parts[i + 1].startswith("-"):
                args[key] = parts[i + 1]
                i += 2
            else:
                args[key] = True
                i += 1
        elif p.startswith("-"):
            key = p[1:].replace("-", "_")
            args[key] = True
            i += 1
        else:
            i += 1
    return args


# --- Core GCL Logic ---

def run_az(command: str, timeout: int = 120) -> GeneratorResult:
    """Execute az command and return structured result."""
    start = time.time()
    try:
        # Split command string into list (handles "az vm show --name x")
        parts = command.split()
        result = subprocess.run(parts, capture_output=True, text=True, timeout=timeout)
        elapsed = time.time() - start
        return GeneratorResult(
            command=command,
            args=parse_args(command),
            exit_code=result.returncode,
            stdout=result.stdout[:4000],
            stderr=result.stderr[:2000],
            elapsed_sec=round(elapsed, 2),
        )
    except subprocess.TimeoutExpired:
        return GeneratorResult(
            command=command, args={}, exit_code=-1,
            stdout="", stderr=f"Timeout after {timeout}s", elapsed_sec=timeout,
        )
    except FileNotFoundError:
        return GeneratorResult(
            command=command, args={}, exit_code=-1,
            stdout="", stderr="az not found. Install Azure CLI: https://aka.ms/installazurecliwindows",
            elapsed_sec=0,
        )


def score(trace: GCLTrace, rubric: dict, destructive: bool) -> CriticResult:
    """
    Deterministic rule-based critic scoring.
    Aligned with AGENTS.md §6 trace schema.
    """
    gen = trace.iterations[-1].generator
    scores = {}
    suggestions = []
    blocking = False

    # Correctness: exit code 0 + non-empty stdout
    if gen.exit_code == 0 and gen.stdout.strip():
        scores["correctness"] = 1.0
    elif gen.exit_code == 0:
        scores["correctness"] = 0.5
        suggestions.append("Command succeeded but stdout is empty — verify resource state")
    else:
        scores["correctness"] = 0.0
        err_brief = mask_credentials(gen.stderr[:200])
        suggestions.append(f"Command failed (exit {gen.exit_code}): {err_brief}")
        blocking = True

    # Safety: destructive ops must have pre-confirmation show
    if destructive:
        prior_shows = sum(
            1 for it in trace.iterations
            if "show" in it.generator.command.lower() and "delete" not in it.generator.command.lower()
        )
        if prior_shows > 0:
            scores["safety"] = 1.0
        else:
            scores["safety"] = 0.0
            suggestions.append("Destructive op without prior `show` — safety gate missing")
            blocking = True
    else:
        scores["safety"] = 1.0

    # Safety override: credential leak
    combined = gen.stdout + gen.stderr
    if "AZURE_CLIENT_SECRET" in combined or "password" in combined.lower():
        # Only flag if it looks like a real credential (not a help message)
        if "create-for-rbac" not in combined and "show" not in gen.command.lower():
            scores["safety"] = 0.0
            suggestions.append("CREDENTIAL_LIKELIHOOD: credential pattern in output")
            blocking = True

    # Idempotency: exit 0 on re-run
    scores["idempotency"] = 1.0 if gen.exit_code == 0 else 0.5

    # Traceability: command + output captured
    if gen.command and gen.stdout:
        scores["traceability"] = 1.0
    elif gen.command:
        scores["traceability"] = 0.5
        suggestions.append("No stdout captured in trace")
    else:
        scores["traceability"] = 0.0
        suggestions.append("No command captured")
        blocking = True

    # Spec compliance: --output json + --resource-group
    has_json = "--output json" in gen.command or "-o json" in gen.command
    has_rg = "--resource-group" in gen.command
    if has_json and has_rg:
        scores["spec_compliance"] = 1.0
    elif has_json:
        scores["spec_compliance"] = 0.5
        suggestions.append("Missing --resource-group")
    else:
        scores["spec_compliance"] = 0.0
        suggestions.append("Missing --output json")
        blocking = True

    # Safety=0 always blocks
    if scores.get("safety", 1.0) == 0.0:
        blocking = True

    return CriticResult(
        scores=CriticScores(**scores),
        suggestions=suggestions[:3],
        blocking=blocking,
    )


def decide(trace: GCLTrace, rubric: dict, max_iter: int, destructive: bool) -> tuple[str, Optional[dict]]:
    """Return (decision, final_entry)."""
    last = trace.iterations[-1]
    s = last.critic.scores
    all_pass = all(
        getattr(s, dim, 0) >= rubric[dim]["threshold"]
        for dim in ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]
    )

    if last.critic.blocking:
        last.decision = "BLOCK"
        return "BLOCK", {
            "status": "SAFETY_FAIL",
            "iter": last.iter,
            "reason": suggestions_summary(last.critic.suggestions),
            "scores": asdict(s),
            "output": mask_credentials(last.generator.stdout[:500]),
        }
    if all_pass:
        last.decision = "PASS"
        return "PASS", {
            "status": "PASS",
            "iter": last.iter,
            "scores": asdict(s),
            "output": mask_credentials(last.generator.stdout[:500]),
        }
    if last.iter >= max_iter:
        last.decision = "MAX_ITER"
        return "MAX_ITER", {
            "status": "MAX_ITER",
            "iter": last.iter,
            "reason": f"max_iter={max_iter} reached",
            "scores": asdict(s),
            "unresolved": [dim for dim in ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]
                          if getattr(s, dim, 0) < rubric[dim]["threshold"]],
        }
    last.decision = "RETRY"
    return "RETRY", None


def suggestions_summary(suggestions: list[str]) -> str:
    return "; ".join(suggestions) if suggestions else "scoring failed"


# --- Trace Persistence ---

def persist(trace: GCLTrace) -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{TRACE_PREFIX}-{ts()}-{uuid.uuid4().hex[:6]}.json"
    path = AUDIT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict_trace(trace), f, indent=2, ensure_ascii=False)
    return path


def asdict_trace(trace: GCLTrace) -> dict:
    """Serialize GCLTrace to dict matching AGENTS.md §6 schema."""
    iterations = []
    for it in trace.iterations:
        iterations.append({
            "iter": it.iter,
            "generator": {
                "command": mask_credentials(it.generator.command),
                "args": it.generator.args,
                "exit_code": it.generator.exit_code,
                "result_excerpt": mask_credentials(it.generator.stdout[:800]),
            },
            "critic": {
                "scores": asdict(it.critic.scores),
                "suggestions": [mask_credentials(s) for s in it.critic.suggestions],
                "blocking": it.critic.blocking,
            },
            "decision": it.decision,
        })
    return {
        "skill": trace.skill,
        "request": mask_credentials(trace.request),
        "rubric_version": trace.rubric_version,
        "iterations": iterations,
        "final": trace.final,
    }


# --- Main ---

def gcl_run(command: str, skill: Optional[str] = None, max_iter: int = 3) -> dict:
    """
    Run one az command through GCL: execute → score → decide → persist.
    Returns the final entry dict.
    """
    skill = skill or detect_skill(command)
    destructive = is_destructive(command)
    rubric = default_rubric(skill, destructive)

    trace = GCLTrace(
        skill=skill,
        request=command,
        rubric_version="v1",
    )

    for i in range(1, max_iter + 1):
        gen_result = run_az(command)
        iter_entry = Iteration(
            iter=i,
            generator=gen_result,
            critic=CriticResult(
                scores=CriticScores(correctness=0, safety=0, idempotency=0, traceability=0, spec_compliance=0),
                suggestions=[],
                blocking=False,
            ),
            decision="RETRY",
        )
        trace.iterations.append(iter_entry)

        # Score
        trace.iterations[-1].critic = score(trace, rubric, destructive)

        # Decide
        decision, final_entry = decide(trace, rubric, max_iter, destructive)
        if decision in ("BLOCK", "PASS", "MAX_ITER"):
            trace.final = final_entry
            break

    # Persist
    path = persist(trace)
    return {
        "status": trace.final["status"] if trace.final else "UNKNOWN",
        "iter": trace.iterations[-1].iter,
        "scores": asdict(trace.iterations[-1].critic.scores),
        "trace": str(path),
        "output": trace.final.get("output", "") if trace.final else "",
        "suggestions": [mask_credentials(s) for s in trace.iterations[-1].critic.suggestions],
    }


def main():
    parser = argparse.ArgumentParser(
        description="az_trace.py — Auto-tracer for Azure CLI. Wraps az commands with GCL scoring.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/az_trace.py run "az vm show --name my-vm --resource-group my-rg --output json"
  python scripts/az_trace.py run --skill azure-vm-ops "az vm delete --name my-vm --resource-group my-rg --yes"
  python scripts/az_trace.py trace  # show last N traces
  python scripts/az_trace.py lint   # score all traces in audit-results/
        """,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # run
    p_run = sub.add_parser("run", help="Execute one az command with auto-tracing")
    p_run.add_argument("--skill", help="Skill name (auto-detected if omitted)")
    p_run.add_argument("--max-iter", type=int, default=3)
    p_run.add_argument("command", help="Full az command as a single string")
    p_run.add_argument("--json", action="store_true", help="Output only JSON")

    # trace
    p_trace = sub.add_parser("trace", help="List recent trace files")
    p_trace.add_argument("-n", "--count", type=int, default=10)

    # lint
    p_lint = sub.add_parser("lint", help="Score all traces in audit-results/ (batch review)")

    args = parser.parse_args()

    if args.cmd == "run":
        result = gcl_run(args.command, skill=args.skill, max_iter=args.max_iter)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[az_trace] skill={result['skill']} status={result['status']} "
                  f"iter={result['iter']} trace={result['trace']}", file=sys.stderr)
            if result["suggestions"]:
                print(f"[az_trace] suggestions: {'; '.join(result['suggestions'])}", file=sys.stderr)
            print(result["output"])

    elif args.cmd == "trace":
        files = sorted(AUDIT_DIR.glob(f"{TRACE_PREFIX}-*.json"), reverse=True)
        if not files:
            print("No traces found. Run: python scripts/az_trace.py run '<az command>'")
            return
        for f in files[:args.count]:
            ts_str = f.stem.replace(f"{TRACE_PREFIX}-", "")
            size = f.stat().st_size
            print(f"  {ts_str}  {size:>6d}B  {f.name}")

    elif args.cmd == "lint":
        files = sorted(AUDIT_DIR.glob(f"{TRACE_PREFIX}-*.json"), reverse=True)
        if not files:
            print("No traces to lint.")
            return
        total = len(files)
        statuses = {"PASS": 0, "SAFETY_FAIL": 0, "MAX_ITER": 0}
        safety_fails = []
        for f in files:
            try:
                data = json.loads(f.read_text())
                s = data.get("final", {}).get("status", "UNKNOWN")
                statuses[s] = statuses.get(s, 0) + 1
                if s == "SAFETY_FAIL":
                    safety_fails.append(f.name)
            except (json.JSONDecodeError, OSError):
                pass
        print(f"Traces: {total} total | PASS: {statuses['PASS']} | "
              f"SAFETY_FAIL: {statuses['SAFETY_FAIL']} | MAX_ITER: {statuses['MAX_ITER']}")
        if safety_fails:
            print(f"Safety failures: {', '.join(safety_fails)}")


if __name__ == "__main__":
    main()
