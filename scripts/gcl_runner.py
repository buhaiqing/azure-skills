#!/usr/bin/env python3
"""
GCL (Generator-Critic-Loop) Runner — Azure Skills

Reusable Orchestrator that wraps `az` calls with isolated Generator/Critic sub-agents.

Usage:
    python scripts/gcl_runner.py <skill_name> <rubric_json> "<user_request>"

Example:
    python scripts/gcl_runner.py azure-vm-ops '{"rubric_version":"v1"}' "Delete VM my-test-vm in rg-test"

Environment:
    AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
"""

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# --- Constants ---

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = REPO_ROOT / "audit-results"
MAX_ITER = 3  # default; overridden per-skill in rubric

DEFAULT_RUBRIC = {
    "correctness": {"scale": [0, 0.5, 1], "threshold": 0.5},
    "safety": {"scale": [0, 1], "threshold": 1},
    "idempotency": {"scale": [0, 0.5, 1], "threshold": 0.5},
    "traceability": {"scale": [0, 0.5, 1], "threshold": 0.5},
    "spec_compliance": {"scale": [0, 0.5, 1], "threshold": 0.5},
}

# GCL_REQUIRED_SKILLS: loaded dynamically from registry
# Skill is REQUIRED if any operation has risky=true
# This avoids hardcoding and stays in sync with registry.json

def _load_gcl_required_skills() -> set:
    """Scan registry.json and return skills with at least one risky=true operation."""
    registry_path = REPO_ROOT / "scripts" / "self_healing" / "registry.json"
    required = set()
    recommended = set()
    try:
        import json
        registry = json.loads(registry_path.read_text())
        for skill, policy_file in registry.get("skills", {}).items():
            policy_path = REPO_ROOT / "scripts" / "self_healing" / policy_file
            if policy_path.exists():
                policy = json.loads(policy_path.read_text())
                risky_ops = [op for op, cfg in policy.get("operations", {}).items() if cfg.get("risky")]
                if risky_ops:
                    required.add(skill)
                else:
                    recommended.add(skill)
    except Exception:
        # Fallback: hardcoded original set
        required = {
            "azure-vm-ops", "azure-aks-ops", "azure-blobstorage-ops",
            "azure-appgateway-ops", "azure-loadbalancer-ops",
            "azure-frontdoor-ops", "azure-trafficmanager-ops",
        }
        recommended = {"azure-monitor-ops", "azure-audit-ops", "azure-cost-ops"}
    return required, recommended

GCL_REQUIRED_SKILLS, GCL_RECOMMENDED_SKILLS = _load_gcl_required_skills()


# --- CADL Finding Reporter ---

def _report_finding(skill: str, failure_type: str, context: dict, trace_id: str) -> None:
    """Write CADL finding on GCL escalation. Silently ignores if report_finding.py unavailable."""
    try:
        import importlib.util
        script = REPO_ROOT / "scripts" / "report_finding.py"
        spec = importlib.util.spec_from_file_location("report_finding", script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.report_finding(
            skill=skill,
            operation="",
            failure_type=failure_type,
            context=context,
            trace_id=trace_id,
        )
    except Exception:
        pass  # non-critical; findings are best-effort


# --- Utilities ---

def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def run_command(cmd: list[str], timeout: int = 120) -> dict:
    """Execute a shell command and return structured output."""
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.time() - start
        return {
            "command": " ".join(cmd),
            "exit_code": result.returncode,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:2000],
            "elapsed_sec": round(elapsed, 2),
        }
    except subprocess.TimeoutExpired:
        return {
            "command": " ".join(cmd),
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Timeout after {timeout}s",
            "elapsed_sec": timeout,
        }
    except FileNotFoundError:
        return {
            "command": " ".join(cmd),
            "exit_code": -1,
            "stdout": "",
            "stderr": "Command not found (az not installed?)",
            "elapsed_sec": 0,
        }


def check_credentials() -> bool:
    """Verify Azure credentials are configured and valid."""
    result = run_command(["az", "account", "show", "--output", "json"])
    if result["exit_code"] != 0:
        print("[ERROR] Azure credentials not configured. Set AZURE_* env vars.", file=sys.stderr)
        return False

    missing = []
    for var in ["AZURE_SUBSCRIPTION_ID", "AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"]:
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        print(f"[ERROR] Missing env vars: {', '.join(missing)}", file=sys.stderr)
        return False

    return True


def resolve_placeholders(text: str, env_vars: dict, user_vars: dict, output_vars: dict) -> str:
    """Resolve {{env.*}}, {{user.*}}, {{output.*}} placeholders."""
    for key, val in env_vars.items():
        text = text.replace(f"{{{{env.{key}}}}}", str(val))
    for key, val in user_vars.items():
        text = text.replace(f"{{{{user.{key}}}}}", str(val))
    for key, val in output_vars.items():
        text = text.replace(f"{{{{output.{key}}}}}", str(val))
    return text


def persist_trace(trace: dict) -> str:
    """Write GCL trace JSON to audit-results/ and return the path."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"gcl-trace-{timestamp()}-{uuid.uuid4().hex[:8]}.json"
    path = AUDIT_DIR / filename
    with open(path, "w") as f:
        json.dump(trace, f, indent=2, default=str)
    return str(path)


# --- Critic Scoring (isolated) ---

def critic_score(trace: dict, rubric: dict) -> dict:
    """
    Independent Critic evaluation.
    Scores each rubric dimension based on the execution trace.
    This is a deterministic rule-based scorer (not an LLM call).
    """
    scores = {}
    suggestions = []
    blocking = False

    # Correctness: exit code 0 + non-empty stdout
    last_iter = trace["iterations"][-1] if trace["iterations"] else {}
    gen = last_iter.get("generator", {})
    if gen.get("exit_code") == 0 and gen.get("stdout", "").strip():
        scores["correctness"] = 1.0
    elif gen.get("exit_code") == 0 and not gen.get("stdout", "").strip():
        scores["correctness"] = 0.5
        suggestions.append("Command succeeded but returned empty output — verify resource state")
    else:
        scores["correctness"] = 0
        suggestions.append(f"Command failed (exit {gen.get('exit_code')}): {gen.get('stderr', '')[:200]}")
        blocking = True

    # Safety: check for destructive patterns with confirmation
    cmd = gen.get("command", "")
    is_destructive = any(kw in cmd for kw in ["delete", "terminate", "destroy", "purge",
                                               "stop", "deallocate", "scale", "--node-count 0"])
    if is_destructive and trace["skill"] in GCL_REQUIRED_SKILLS:
        trace_has_show = any("show" in it.get("generator", {}).get("command", "")
                             for it in trace["iterations"])
        if trace_has_show:
            scores["safety"] = 1.0
        else:
            scores["safety"] = 0
            suggestions.append("Destructive operation without pre-delete `show` — safety gate missing")
            blocking = True
    else:
        # Non-destructive or optional skill
        scores["safety"] = 1.0

    # Safety override: credential leak detection
    output_text = gen.get("stdout", "") + gen.get("stderr", "")
    if "AZURE_CLIENT_SECRET" in output_text:
        scores["safety"] = 0
        suggestions.append("CREDENTIAL_LEAK: AZURE_CLIENT_SECRET found in output")
        blocking = True

    # Idempotency: re-run check (if we have >1 iteration with same command)
    if len(trace["iterations"]) >= 2:
        prev_cmd = trace["iterations"][-2].get("generator", {}).get("command", "")
        curr_cmd = gen.get("command", "")
        if prev_cmd == curr_cmd and gen.get("exit_code") == 0:
            scores["idempotency"] = 1.0
        elif prev_cmd == curr_cmd:
            scores["idempotency"] = 0.5
            suggestions.append("Re-running same command produced different result")
        else:
            scores["idempotency"] = 0.5
    else:
        # Single run — assume idempotent if success
        scores["idempotency"] = 1.0 if gen.get("exit_code") == 0 else 0.5

    # Traceability: trace completeness
    if gen.get("command") and gen.get("stdout"):
        scores["traceability"] = 1.0
    elif gen.get("command"):
        scores["traceability"] = 0.5
        suggestions.append("Output or stderr not captured in trace")
    else:
        scores["traceability"] = 0
        suggestions.append("No command captured in trace")
        blocking = True

    # Spec compliance: --output json present, --resource-group present
    if "--output json" in cmd or "-o json" in cmd:
        rg_check = "--resource-group" in cmd or "--resource-group " in cmd
        scores["spec_compliance"] = 1.0 if rg_check else 0.5
        if not rg_check:
            suggestions.append("Missing --resource-group parameter")
    else:
        scores["spec_compliance"] = 0
        suggestions.append("Missing --output json flag")
        blocking = True

    # Safety=0 → force ABORT
    if scores.get("safety", 1) == 0:
        blocking = True

    return {
        "scores": scores,
        "suggestions": suggestions[:3],
        "blocking": blocking,
    }


# --- Main Orchestrator ---

def orchestrate(skill: str, user_request: str, rubric: dict | None = None) -> dict:
    """Main GCL loop: G → C → Decide → (loop|return)."""
    if not check_credentials():
        return {"status": "ABORT", "reason": "Credential check failed"}

    rubric = rubric or DEFAULT_RUBRIC
    max_iter = rubric.get("max_iter", MAX_ITER)
    skill_required = skill in GCL_REQUIRED_SKILLS

    trace_id = uuid.uuid4().hex[:8]
    trace = {
        "id": trace_id,
        "skill": skill,
        "request": user_request,
        "rubric_version": rubric.get("rubric_version", "v1"),
        "iterations": [],
        "final": {},
    }

    env_vars = {k: os.environ.get(k, "") for k in
                ["AZURE_SUBSCRIPTION_ID", "AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"]}

    for iteration in range(1, max_iter + 1):
        print(f"\n[GCL] Iteration {iteration}/{max_iter} — skill={skill}")

        # --- GENERATOR ---
        resolved_cmd = resolve_placeholders(user_request, env_vars, {}, {})
        # Split the resolved request into shell args
        cmd_parts = resolved_cmd.split()
        if not cmd_parts:
            print("[GCL] Empty command — using default `az account show`")
            cmd_parts = ["az", "account", "show", "--output", "json"]

        gen_result = run_command(cmd_parts)

        iter_entry = {
            "iter": iteration,
            "generator": gen_result,
            "critic": {},
            "decision": "RETRY",
        }

        # --- CRITIC ---
        critic_result = critic_score(trace, rubric)
        iter_entry["critic"] = {
            "scores": critic_result["scores"],
            "suggestions": critic_result["suggestions"],
            "blocking": critic_result["blocking"],
        }

        trace["iterations"].append(iter_entry)

        # --- DECIDE ---
        scores = critic_result["scores"]

        # Safety=0 → ABORT
        if scores.get("safety", 1) == 0 and skill_required:
            trace["final"] = {
                "status": "SAFETY_FAIL",
                "iter": iteration,
                "reason": "Safety=0 — destructive operation without confirmation gate",
                "scores": scores,
            }
            _path = persist_trace(trace)
            tid = trace["id"]
            _report_finding(
                skill=skill,
                failure_type="gcl_safety_fail",
                context={"reason": trace["final"]["reason"], "scores": scores},
                trace_id=tid,
            )
            print(f"[GCL] SAFETY_FAIL — trace written to {_path}")
            return trace["final"]

        # All pass
        all_pass = all(
            scores.get(dim, 0) >= rubric.get(dim, {}).get("threshold", 0.5)
            for dim in ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]
        )
        if all_pass:
            trace["final"] = {
                "status": "PASS",
                "iter": iteration,
                "scores": scores,
                "output": gen_result.get("stdout", "")[:500],
            }
            _path = persist_trace(trace)
            print(f"[GCL] PASS — trace written to {_path}")
            return trace["final"]

        # Suggestions for next iteration
        suggestions = critic_result.get("suggestions", [])
        if suggestions:
            print(f"[GCL] Suggestions: {'; '.join(suggestions)}")

    # MAX_ITER reached
    trace["final"] = {
        "status": "MAX_ITER",
        "iter": max_iter,
        "reason": f"Reached max_iter={max_iter} without passing all rubric dimensions",
        "scores": critic_result["scores"] if 'critic_result' in dir() else {},
    }
    _path = persist_trace(trace)
    tid = trace["id"]
    _report_finding(
        skill=skill,
        failure_type="gcl_max_iter",
        context={"reason": trace["final"]["reason"], "scores": trace["final"]["scores"]},
        trace_id=tid,
    )
    print(f"[GCL] MAX_ITER — trace written to {_path}")
    return trace["final"]


# --- CLI Entry Point ---

def main():
    if len(sys.argv) < 3:
        print("Usage: python gcl_runner.py <skill_name> [rubric_json] \"<user_request>\"")
        print("")
        print("Examples:")
        print("  python gcl_runner.py azure-vm-ops '{\"rubric_version\":\"v1\"}' \"az vm show --name my-vm --resource-group my-rg --output json\"")
        print("  python gcl_runner.py azure-aks-ops '{}' \"az aks list --output json\"")
        sys.exit(1)

    skill = sys.argv[1]
    rubric_json = sys.argv[2] if len(sys.argv) > 2 else "{}"
    user_request = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""

    rubric = json.loads(rubric_json)
    rubric.setdefault("max_iter", MAX_ITER)

    result = orchestrate(skill, user_request, rubric)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()