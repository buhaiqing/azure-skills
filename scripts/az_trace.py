#!/usr/bin/env python3
"""
az_trace.py — Lightweight auto-tracer for Azure CLI

Drop-in wrapper that intercepts `az` commands, scores them against the GCL rubric,
and persists normalized traces to audit-results/.

Schema aligned with Langfuse observation model (trace → span → generation).
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

# --- Langfuse Schema Alignment ---
# Trace-level reserved fields (snake_case = Python SDK convention):
#   id, name, user_id, session_id, version, release, metadata, tags, public, input, output
# Observation fields (snake_case):
#   id, trace_id, name, type, start_time, end_time, metadata
#   generation: model, model_parameters, input, output, usage, completion_start_time
# For rule-based scoring (no LLM): model = "rule-based-az-cli"

TRACE_VERSION = "1.0.0"

# --- Constants ---

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = REPO_ROOT / "audit-results"
TRACE_PREFIX = "gcl-trace"
TIMESTAMP_FMT = "%Y%m%d-%H%M%S"

# Skills where GCL is REQUIRED
GCL_REQUIRED_SKILLS = frozenset({
    "azure-vm-ops", "azure-aks-ops", "azure-blobstorage-ops",
    "azure-appgateway-ops", "azure-loadbalancer-ops", "azure-frontdoor-ops",
    "azure-trafficmanager-ops", "azure-backup-ops", "azure-dns-ops",
    "azure-file-storage-ops", "azure-queue-storage-ops", "azure-site-recovery-ops",
    "azure-eventgrid-ops", "azure-apim-ops",
})

DESTRUCTIVE_PATTERNS = re.compile(
    r"\b(delete|terminate|destroy|purge|remove|stop\s+--?\s*deallocate|"
    r"deallocate|drop\s+table|drop\s+database|reset|purge\s+key|"
    r"scale\s+-+\s*0|node-count\s+0|--yes\s+-\s*y|--force-deletion)\b",
    re.IGNORECASE,
)

CREDENTIAL_PATTERNS = re.compile(
    r"(AZURE_CLIENT_SECRET|AZURE_|subscription[_-]?id|tenant[_-]?id|"
    r"client[_-]?id|client[_-]?secret|access[_-]?key|connection[_-]?string|"
    r"password|token|Bearer\s+[a-zA-Z0-9._-]+)",
    re.IGNORECASE,
)

AZ_TO_SKILL = {
    "vm": "azure-vm-ops", "aks": "azure-aks-ops",
    "storage account": "azure-blobstorage-ops",
    "storage container": "azure-blobstorage-ops",
    "storage blob": "azure-blobstorage-ops",
    "storage share": "azure-file-storage-ops",
    "storage queue": "azure-queue-storage-ops",
    "network application-gateway": "azure-appgateway-ops",
    "network lb": "azure-loadbalancer-ops",
    "afd": "azure-frontdoor-ops",
    "network traffic-manager": "azure-trafficmanager-ops",
    "backup": "azure-backup-ops", "site-recovery": "azure-site-recovery-ops",
    "network dns": "azure-dns-ops", "eventhubs": "azure-eventhub-ops",
    "eventgrid": "azure-eventgrid-ops", "servicebus": "azure-servicebus-ops",
    "functionapp": "azure-function-ops", "webapp": "azure-appservice-ops",
    "containerapp": "azure-aci-ops", "containerreg": "azure-acr-ops",
    "cosmosdb": "azure-cosmos-ops", "sql": "azure-sqldb-ops",
    "postgres": "azure-postgres-ops", "redis": "azure-redis-ops",
    "keyvault": "azure-keyvault-ops", "monitor": "azure-monitor-ops",
    "policy": "azure-audit-ops", "role": "azure-audit-ops",
    "lock": "azure-audit-ops", "group": "azure-vnet-ops",
    "network vnet": "azure-vnet-ops", "network nsg": "azure-nsg-ops",
    "network private-endpoint": "azure-privateendpoint-ops",
    "apim": "azure-apim-ops",
}


# --- Data Models (Langfuse-aligned) ---

@dataclass
class GCLScores:
    correctness: float
    safety: float
    idempotency: float
    traceability: float
    spec_compliance: float


@dataclass
class Generation:
    """Langfuse GENERATION observation — represents az command execution."""
    model: str = "rule-based-az-cli"      # no LLM; would be "gpt-4o" if upgraded
    model_parameters: dict = field(default_factory=dict)
    input: str = ""
    output: str = ""
    usage: dict = field(default_factory=dict)  # for LLM: prompt_tokens/completion_tokens; here: az metadata
    metadata: dict = field(default_factory=dict)


@dataclass
class Span:
    """Langfuse SPAN observation — represents one GCL iteration."""
    name: str = ""       # e.g. "iter-1"
    start_time: str = ""  # ISO8601
    end_time: str = ""    # ISO8601
    metadata: dict = field(default_factory=dict)
    generation: Optional[Generation] = None
    # GCL-specific: critic scores attached to span metadata
    gcl_scores: Optional[GCLScores] = None
    gcl_suggestions: list = field(default_factory=list)
    gcl_blocking: bool = False
    gcl_decision: str = ""


@dataclass
class Trace:
    """
    Langfuse Trace — top-level container for one GCL run.
    Fields align with Langfuse Python SDK snake_case convention.
    """
    id: str = ""
    name: str = ""         # trace name, e.g. "azure-vm-ops GCL"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    version: str = TRACE_VERSION
    release: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    tags: list = field(default_factory=list)
    public: bool = False
    input: str = ""
    output: str = ""
    # GCL-specific spans
    spans: list = field(default_factory=list)
    # Summary fields (flat, for quick query)
    gcl_status: str = ""    # PASS / SAFETY_FAIL / MAX_ITER
    gcl_final_iter: int = 0


# --- Helpers ---

def ts() -> str:
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FMT)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def mask_credentials(text: str) -> str:
    return CREDENTIAL_PATTERNS.sub("***", text)


def is_destructive(command: str) -> bool:
    return bool(DESTRUCTIVE_PATTERNS.search(command))


def detect_skill(command: str) -> str:
    lower = command.lower()
    for pattern, skill in AZ_TO_SKILL.items():
        if pattern in lower:
            return skill
    return "unknown"


def default_rubric(skill: str, destructive: bool) -> dict:
    required = skill in GCL_REQUIRED_SKILLS
    safety_threshold = 1.0 if (required or destructive) else 0.5
    return {
        "correctness": {"threshold": 0.5},
        "safety": {"threshold": safety_threshold},
        "idempotency": {"threshold": 0.5},
        "traceability": {"threshold": 0.5},
        "spec_compliance": {"threshold": 0.5},
    }


def parse_args(command: str) -> dict:
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
            args[p[1:].replace("-", "_")] = True
            i += 1
        else:
            i += 1
    return args


# --- Core GCL Logic ---

def run_az(command: str, timeout: int = 120) -> dict:
    start = time.time()
    start_iso = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    try:
        result = subprocess.run(command.split(), capture_output=True, text=True, timeout=timeout)
        elapsed = time.time() - start
        end_iso = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        return {
            "start_iso": start_iso, "end_iso": end_iso,
            "elapsed": round(elapsed, 3),
            "exit_code": result.returncode,
            "stdout": result.stdout[:4000],
            "stderr": result.stderr[:2000],
            "command": command,
        }
    except subprocess.TimeoutExpired:
        end_iso = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        return {
            "start_iso": start_iso, "end_iso": end_iso, "elapsed": timeout,
            "exit_code": -1, "stdout": "",
            "stderr": f"Timeout after {timeout}s", "command": command,
        }
    except FileNotFoundError:
        end_iso = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        return {
            "start_iso": start_iso, "end_iso": end_iso, "elapsed": 0,
            "exit_code": -1, "stdout": "",
            "stderr": "az not found. Install: https://aka.ms/installazurecliwindows",
            "command": command,
        }


def score(gen_result: dict, rubric: dict, destructive: bool, prev_command: str = "") -> tuple[GCLScores, list, bool]:
    scores = {"correctness": 0.0, "safety": 1.0, "idempotency": 0.5, "traceability": 0.5, "spec_compliance": 0.5}
    suggestions = []
    blocking = False

    # Correctness
    if gen_result["exit_code"] == 0 and gen_result["stdout"].strip():
        scores["correctness"] = 1.0
    elif gen_result["exit_code"] == 0:
        scores["correctness"] = 0.5
        suggestions.append("Command succeeded but stdout is empty")
    else:
        scores["correctness"] = 0.0
        suggestions.append(f"Command failed (exit {gen_result['exit_code']}): {mask_credentials(gen_result['stderr'][:200])}")
        if destructive:
            blocking = True

    # Safety: destructive ops must have prior `show`
    if destructive:
        # Heuristic: command contains "show" and not "delete" = pre-confirmation
        if "show" in gen_result["command"].lower() and "delete" not in gen_result["command"].lower():
            scores["safety"] = 1.0
        else:
            scores["safety"] = 0.0
            suggestions.append("Destructive op without prior `show` — safety gate missing")
            blocking = True

    # Credential leak: only flag credential-write operations
    credential_write_ops = (
        "create-for-rbac" in gen_result["command"] or
        "create-credentials" in gen_result["command"] or
        "reset-credentials" in gen_result["command"]
    )
    combined = gen_result["stdout"] + gen_result["stderr"]
    if credential_write_ops and ("AZURE_CLIENT_SECRET" in combined or "password" in combined.lower()):
        scores["safety"] = 0.0
        suggestions.append("CREDENTIAL_LEAK: secret value found in credential-write output")
        blocking = True

    # Idempotency
    if prev_command and gen_result["command"] == prev_command:
        scores["idempotency"] = 1.0 if gen_result["exit_code"] == 0 else 0.5
    elif not prev_command:
        scores["idempotency"] = 1.0 if gen_result["exit_code"] == 0 else 0.5
    else:
        # Command was mechanically fixed between iterations — not a failure
        scores["idempotency"] = 1.0

    # Traceability
    if gen_result["command"] and gen_result["stdout"]:
        scores["traceability"] = 1.0
    elif gen_result["command"]:
        scores["traceability"] = 0.5
        suggestions.append("No stdout captured in trace")
    else:
        scores["traceability"] = 0.0
        suggestions.append("No command captured")
        blocking = True

    # Spec compliance
    has_json = "--output json" in gen_result["command"] or "-o json" in gen_result["command"]
    has_rg = "--resource-group" in gen_result["command"]
    if has_json and has_rg:
        scores["spec_compliance"] = 1.0
    elif has_json:
        scores["spec_compliance"] = 0.5
        suggestions.append("Missing --resource-group")
    else:
        scores["spec_compliance"] = 0.0
        suggestions.append("Missing --output json")

    if scores["safety"] == 0.0:
        blocking = True

    return GCLScores(**scores), suggestions[:3], blocking


def decide(scores: GCLScores, rubric: dict, iter_num: int, max_iter: int) -> tuple[str, dict]:
    all_pass = all(
        getattr(scores, dim, 0) >= rubric[dim]["threshold"]
        for dim in ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]
    )
    if all_pass:
        return "PASS", {"status": "PASS", "iter": iter_num, "scores": asdict(scores)}
    if iter_num >= max_iter:
        unresolved = [d for d in ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]
               if getattr(scores, d, 0) < rubric[d]["threshold"]]
        return "MAX_ITER", {"status": "MAX_ITER", "iter": iter_num, "unresolved": unresolved, "scores": asdict(scores)}
    return "RETRY", {}


# --- Command Fixer ---

def _inject_output_json(cmd: str) -> str:
    if "--output" not in cmd and "-o json" not in cmd and "-o table" not in cmd:
        return f"{cmd.rstrip()} --output json"
    return cmd


def _fix_command(cmd: str, suggestions: list[str]) -> str:
    for s in suggestions:
        if "Missing --output json" in s:
            cmd = _inject_output_json(cmd)
    return cmd


# --- Trace Serialization (Langfuse-aligned) ---

def serialize_trace(trace: Trace) -> dict:
    """Serialize Trace to Langfuse-aligned dict."""
    result = {
        "id": trace.id,
        "name": trace.name,
        "version": trace.version,
        "metadata": trace.metadata,
        "gcl_status": trace.gcl_status,
        "gcl_final_iter": trace.gcl_final_iter,
        "input": mask_credentials(trace.input),
        "output": mask_credentials(trace.output),
        "spans": [],
    }
    if trace.user_id:
        result["user_id"] = trace.user_id
    if trace.session_id:
        result["session_id"] = trace.session_id
    if trace.release:
        result["release"] = trace.release
    if trace.tags:
        result["tags"] = trace.tags

    for span in trace.spans:
        span_dict = {
            "name": span.name,
            "start_time": span.start_time,
            "end_time": span.end_time,
            "metadata": span.metadata,
        }
        if span.generation:
            gen = span.generation
            span_dict["generation"] = {
                "model": gen.model,
                "model_parameters": gen.model_parameters,
                "input": mask_credentials(gen.input),
                "output": mask_credentials(gen.output),
                "usage": gen.usage,
                "metadata": gen.metadata,
            }
        if span.gcl_scores:
            span_dict["gcl_scores"] = asdict(span.gcl_scores)
        if span.gcl_suggestions:
            span_dict["gcl_suggestions"] = [mask_credentials(s) for s in span.gcl_suggestions]
        if span.gcl_decision:
            span_dict["gcl_decision"] = span.gcl_decision
        result["spans"].append(span_dict)

    return result


def persist(trace: Trace) -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{TRACE_PREFIX}-{ts()}-{trace.id[:8]}.json"
    path = AUDIT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serialize_trace(trace), f, indent=2, ensure_ascii=False)
    return path


# --- Main ---

def gcl_run(command: str, skill: Optional[str] = None, max_iter: int = 3) -> dict:
    skill = skill or detect_skill(command)
    destructive = is_destructive(command)
    rubric = default_rubric(skill, destructive)

    trace = Trace(
        id=str(uuid.uuid4()),
        name=f"{skill} GCL",
        metadata={
            "skill": skill,
            "is_destructive": destructive,
            "tool": "az_trace.py",
            "tool_version": TRACE_VERSION,
            "scorer": "rule-based",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "os": sys.platform,
        },
        input=command,
        tags=[skill, "gcl", "az-cli"],
    )
    if sub_id := os.environ.get("AZURE_SUBSCRIPTION_ID"):
        parts = sub_id.split("-")
        trace.metadata["subscription_id_pattern"] = f"{parts[0]}-****-{parts[-1]}" if len(parts) >= 3 else "***"

    prev_command = ""
    final_status = "UNKNOWN"
    final_scores = {}

    for i in range(1, max_iter + 1):
        gen_result = run_az(command)

        # Build Generation observation
        generation = Generation(
            model="rule-based-az-cli",  # would be actual model name if upgraded to LLM
            model_parameters={"command": mask_credentials(command)},
            input=mask_credentials(gen_result["command"]),
            output=mask_credentials(gen_result["stdout"][:800]),
            usage={
                "az_exit_code": gen_result["exit_code"],
                "az_elapsed_sec": gen_result["elapsed"],
            },
            metadata={
                "az_stderr": mask_credentials(gen_result["stderr"][:500]),
                "az_args": parse_args(gen_result["command"]),
            },
        )

        # Score
        gcl_scores, suggestions, blocking = score(gen_result, rubric, destructive, prev_command)

        # Decide
        decision, final_entry = decide(gcl_scores, rubric, i, max_iter)

        # Build Span observation
        span = Span(
            name=f"iter-{i}",
            start_time=gen_result["start_iso"],
            end_time=gen_result["end_iso"],
            metadata={
                "command": mask_credentials(gen_result["command"]),
                "exit_code": gen_result["exit_code"],
                "elapsed_sec": gen_result["elapsed"],
            },
            generation=generation,
            gcl_scores=gcl_scores,
            gcl_suggestions=suggestions,
            gcl_blocking=blocking,
            gcl_decision=decision,
        )
        trace.spans.append(span)

        if decision == "PASS":
            trace.gcl_status = "PASS"
            trace.gcl_final_iter = i
            trace.output = mask_credentials(gen_result["stdout"][:500])
            final_status = "PASS"
            final_scores = asdict(gcl_scores)
            break

        if decision == "MAX_ITER":
            trace.gcl_status = "MAX_ITER"
            trace.gcl_final_iter = i
            final_status = "MAX_ITER"
            final_scores = asdict(gcl_scores)
            break

        if blocking:
            trace.gcl_status = "SAFETY_FAIL"
            trace.gcl_final_iter = i
            final_status = "SAFETY_FAIL"
            final_scores = asdict(gcl_scores)
            break

        # Inject fixes into next iteration
        command = _fix_command(command, suggestions)
        prev_command = gen_result["command"]

    path = persist(trace)
    return {
        "id": trace.id,
        "gcl_status": trace.gcl_status,
        "gcl_final_iter": trace.gcl_final_iter,
        "scores": final_scores,
        "trace": str(path),
        "metadata": trace.metadata,
        "output": trace.output,
    }


# --- CLI Entry Point ---

def main():
    parser = argparse.ArgumentParser(
        description="az_trace.py — GCL auto-tracer for Azure CLI. Schema aligned with Langfuse.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/az_trace.py run "az vm show --name my-vm --resource-group my-rg --output json"
  python scripts/az_trace.py run --skill azure-vm-ops "az vm delete --name my-vm --resource-group my-rg --yes"
  python scripts/az_trace.py trace  # list recent traces
  python scripts/az_trace.py lint   # batch score all traces
        """,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Execute one az command with GCL auto-tracing")
    p_run.add_argument("--skill", help="Skill name (auto-detected if omitted)")
    p_run.add_argument("--max-iter", type=int, default=3)
    p_run.add_argument("command", help="Full az command as a single string")
    p_run.add_argument("--json", action="store_true", help="Output only JSON")

    p_trace = sub.add_parser("trace", help="List recent trace files")
    p_trace.add_argument("-n", "--count", type=int, default=10)

    p_lint = sub.add_parser("lint", help="Batch review all traces in audit-results/")

    args = parser.parse_args()

    if args.cmd == "run":
        result = gcl_run(args.command, skill=args.skill, max_iter=args.max_iter)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[az_trace] id={result['id']} status={result['gcl_status']} "
                  f"iter={result['gcl_final_iter']} trace={result['trace']}", file=sys.stderr)
            print(result["output"])

    elif args.cmd == "trace":
        files = sorted(AUDIT_DIR.glob(f"{TRACE_PREFIX}-*.json"), reverse=True)
        if not files:
            print("No traces found.")
            return
        for f in files[:args.count]:
            size = f.stat().st_size
            print(f"  {f.name}  {size:>6d}B")

    elif args.cmd == "lint":
        files = sorted(AUDIT_DIR.glob(f"{TRACE_PREFIX}-*.json"), reverse=True)
        if not files:
            print("No traces to lint.")
            return
        statuses = {"PASS": 0, "SAFETY_FAIL": 0, "MAX_ITER": 0, "UNKNOWN": 0}
        for f in files:
            try:
                data = json.loads(f.read_text())
                s = data.get("gcl_status", "UNKNOWN")
                statuses[s] = statuses.get(s, 0) + 1
            except (json.JSONDecodeError, OSError):
                pass
        total = len(files)
        print(f"Traces: {total} total | PASS: {statuses['PASS']} | "
              f"SAFETY_FAIL: {statuses['SAFETY_FAIL']} | MAX_ITER: {statuses['MAX_ITER']}")


if __name__ == "__main__":
    main()
