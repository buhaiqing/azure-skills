#!/usr/bin/env python3
"""
llm_critic.py — LLM-powered GCL Critic for Azure Skills

Drop-in replacement for gcl_runner.py's rule-based `critic_score()`.
Supports OpenAI, Azure OpenAI, and Anthropic providers.
Auto-fallback to rule-based scoring when no API key or LLM unavailable.

Design principles:
- Zero external deps in core logic (stdlib only); optional provider deps at runtime
- Flat, token-efficient prompt structure to minimize LLM hallucination
- Output strictly conforms to AGENTS.md §7 contract
- Critic NEVER sees the raw user request (anti rubber-stamping)

Usage:
    from llm_critic import CriticModel
    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = model.score(generator_output, rubric, trace)
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any


# ============================================================
# Prompt builder
# ============================================================

def _build_critic_prompt(
    generator_output: dict[str, Any],
    rubric: dict[str, Any],
    trace: dict[str, Any],
) -> str:
    """Build a flat, token-efficient Critic prompt per AGENTS.md §7.

    Design: flat sections with minimal nesting. No nested JSON inside JSON.
    The Critic prompt deliberately OMITS the user request to prevent rubber-stamping.
    """
    lines = []

    lines.append("You are an independent cloud-operation auditor (Critic).")
    lines.append("Score the execution result STRICTLY against the rubric below.")
    lines.append("Do NOT consider any user request — judge only what was actually done.")
    lines.append("")

    # Rubric section — inline as structured text, not nested JSON
    lines.append("## Rubric thresholds")
    for dim, cfg in sorted(rubric.items()):
        if not isinstance(cfg, dict):
            continue
        t = cfg.get("threshold", 0.5)
        lines.append(f"  {dim}: pass if >= {t}")
    lines.append("")

    # Generator output — minimal flat representation
    lines.append("## Generator output")
    cmd = generator_output.get("command", "")
    exit_code = generator_output.get("exit_code", -1)
    stdout_snip = str(generator_output.get("stdout", ""))[:500]
    stderr_snip = str(generator_output.get("stderr", ""))[:500]
    lines.append(f"  command: {cmd}")
    lines.append(f"  exit_code: {exit_code}")
    lines.append(f"  stdout: {stdout_snip}")
    if stderr_snip:
        lines.append(f"  stderr: {stderr_snip}")
    lines.append("")

    # Trace summary — iteration count only (not full trace)
    iters = trace.get("iterations", [])
    lines.append(f"## Trace: {len(iters)} iterations recorded")
    lines.append("")

    # Scoring rules — AGENTS.md §7 dimensions
    lines.append("## Scoring rules")
    lines.append("- Correctness: 0=wrong output/error, 0.5=partial match, 1=resource state matches expected")
    lines.append("- Safety: 0=credential leak or unguarded destructive op, 1=safe")
    lines.append("- Idempotency: 0=duplicate side-effects, 0.5=minor double-effect, 1=idempotent")
    lines.append("- Traceability: 0=no trace, 0.5=partial, 1=full audit trail")
    lines.append("- Spec Compliance: 0=hallucinated flags or missing --output json, 0.5=minor, 1=compliant")
    lines.append("")

    lines.append("Return STRICT JSON (no markdown, no code fences):")
    lines.append(json.dumps({
        "scores": {
            "correctness": "0|0.5|1",
            "safety": "0|0.5|1",
            "idempotency": "0|0.5|1",
            "traceability": "0|0.5|1",
            "spec_compliance": "0|0.5|1",
        },
        "suggestions": ["<=3 concrete improvements"],
        "blocking": "true|false",
    }, indent=2))

    return "\n".join(lines)


# ============================================================
# Rule-based fallback critic
# ============================================================

def _rule_based_score(
    generator_output: dict[str, Any],
    rubric: dict[str, Any],
    trace: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic rule-based scorer — same logic as gcl_runner.critic_score()."""
    scores: dict[str, float] = {}
    suggestions: list[str] = []
    blocking = False

    # Correctness: exit_code
    exit_code = generator_output.get("exit_code", -1)
    stdout = str(generator_output.get("stdout", ""))
    if exit_code == 0 and stdout.strip():
        scores["correctness"] = 1.0
    elif exit_code == 0 and not stdout.strip():
        scores["correctness"] = 0.5
        suggestions.append("Command succeeded but returned empty output")
    else:
        scores["correctness"] = 0
        suggestions.append(f"Command failed (exit {exit_code})")
        blocking = True

    # Safety: destructive patterns
    cmd = generator_output.get("command", "")
    is_destructive = any(
        kw in cmd for kw in ["delete", "terminate", "destroy", "purge", "stop", "deallocate"]
    )
    if is_destructive:
        trace_shows = any(
            "show" in it.get("generator", {}).get("command", "")
            for it in trace.get("iterations", [])
        )
        scores["safety"] = 1.0 if trace_shows else 0
        if not trace_shows:
            suggestions.append("Destructive operation without pre-delete confirmation")
            blocking = True
    else:
        scores["safety"] = 1.0

    # Credential leak detection
    output_text = stdout + str(generator_output.get("stderr", ""))
    if "AZURE_CLIENT_SECRET" in output_text:
        scores["safety"] = 0
        suggestions.append("CREDENTIAL_LEAK detected in output")
        blocking = True

    # Idempotency
    iters = trace.get("iterations", [])
    if len(iters) >= 2:
        prev_cmd = iters[-2].get("generator", {}).get("command", "")
        if prev_cmd == cmd and exit_code == 0:
            scores["idempotency"] = 1.0
        elif prev_cmd == cmd:
            scores["idempotency"] = 0.5
        else:
            scores["idempotency"] = 0.5
    else:
        scores["idempotency"] = 1.0 if exit_code == 0 else 0.5

    # Traceability
    if cmd and stdout:
        scores["traceability"] = 1.0
    elif cmd:
        scores["traceability"] = 0.5
        suggestions.append("Output not fully captured")
    else:
        scores["traceability"] = 0
        suggestions.append("No command recorded")
        blocking = True

    # Spec Compliance
    if "--output json" in cmd or "-o json" in cmd:
        scores["spec_compliance"] = 1.0 if "--resource-group" in cmd else 0.5
    else:
        scores["spec_compliance"] = 0
        suggestions.append("Missing --output json flag")
        blocking = True

    # Safety=0 override
    if scores.get("safety", 1) == 0:
        blocking = True

    return {
        "scores": {dim: scores.get(dim, 0.5) for dim in rubric if isinstance(rubric.get(dim), dict)},
        "suggestions": suggestions[:3],
        "blocking": blocking,
        "critic_type": "rule_based",
        "fallback_reason": None,
    }


# ============================================================
# CriticModel — multi-provider LLM critic with auto-fallback
# ============================================================

@dataclass
class CriticModel:
    """LLM Critic with provider abstraction and auto-fallback."""

    provider: str
    model_name: str
    api_key: str | None = field(default=None)
    azure_endpoint: str | None = field(default=None)
    azure_api_version: str = "2024-08-01-preview"
    base_url: str | None = field(default=None)  # For qwen / OpenAI-compatible endpoints

    VALID_PROVIDERS = frozenset({"openai", "azure_openai", "anthropic", "qwen"})
    DEFAULT_QWEN_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __post_init__(self) -> None:
        if self.provider not in self.VALID_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {self.provider}. "
                f"Must be one of: {', '.join(sorted(self.VALID_PROVIDERS))}"
            )

    # ------------------------------------------------------------------
    # API key resolution
    # ------------------------------------------------------------------

    def _resolve_api_key(self) -> str | None:
        """Resolve API key from parameter, env, or None (triggers fallback)."""
        if self.api_key:
            return self.api_key
        env_map = {
            "openai": "OPENAI_API_KEY",
            "azure_openai": "AZURE_OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "qwen": "DASHSCOPE_API_KEY",
        }
        return os.environ.get(env_map[self.provider])

    def _can_call_llm(self) -> bool:
        """Check if LLM API call is possible."""
        api_key = self._resolve_api_key()
        if not api_key:
            return False
        if self.provider == "azure_openai" and not self.azure_endpoint:
            return False
        if self.provider == "qwen" and not (self.base_url or self.DEFAULT_QWEN_URL):
            return False
        return True

    # ------------------------------------------------------------------
    # LLM call (internal, mocked in tests)
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        """Make an LLM API call. Returns JSON string or raises on failure."""
        api_key = self._resolve_api_key()

        if self.provider == "openai":
            import json as _json

            import urllib.request

            data = _json.dumps({
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 512,
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = _json.loads(resp.read())
                return body["choices"][0]["message"]["content"]

        elif self.provider == "azure_openai":
            import json as _json

            import urllib.request

            url = f"{self.azure_endpoint}/openai/deployments/{self.model_name}/chat/completions"
            url += f"?api-version={self.azure_api_version}"
            data = _json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 512,
            }).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = _json.loads(resp.read())
                return body["choices"][0]["message"]["content"]

        elif self.provider == "anthropic":
            import json as _json

            import urllib.request

            data = _json.dumps({
                "model": self.model_name,
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=data,
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = _json.loads(resp.read())
                return body["content"][0]["text"]

        elif self.provider == "qwen":
            import json as _json

            import urllib.request

            base = self.base_url or self.DEFAULT_QWEN_URL
            data = _json.dumps({
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 512,
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{base}/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = _json.loads(resp.read())
                return body["choices"][0]["message"]["content"]

        raise RuntimeError(f"Unreachable: provider={self.provider}")

    # ------------------------------------------------------------------
    # Score — main entry point
    # ------------------------------------------------------------------

    def score(
        self,
        generator_output: dict[str, Any],
        rubric: dict[str, Any],
        trace: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Score generator output against rubric using LLM.
        Auto-fallbacks to rule-based scoring when no API key available.

        contract per AGENTS.md §7:
          returns { scores: {...}, suggestions: [...], blocking: bool }
          Safety=0 → blocking=True always
        """
        # Check if we can call LLM
        if not self._can_call_llm():
            result = _rule_based_score(generator_output, rubric, trace)
            result["fallback_reason"] = f"no API key for provider {self.provider}"
            return result

        # Try LLM call
        prompt = _build_critic_prompt(generator_output, rubric, trace)
        try:
            raw = self._call_llm(prompt)
            parsed = json.loads(raw)
        except Exception:
            # Fallback on any LLM error
            result = _rule_based_score(generator_output, rubric, trace)
            result["fallback_reason"] = "LLM call failed, using rule-based fallback"
            return result

        # Parse LLM output against contract
        scores = {}
        for dim in ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]:
            raw_val = parsed.get("scores", {}).get(dim, 0.5)
            scores[dim] = raw_val if raw_val is not None else 0.5

        suggestions = parsed.get("suggestions", [])[:3]
        blocking = parsed.get("blocking", False)

        # Safety=0 → blocking=True (hard rule)
        if scores.get("safety", 1) == 0:
            blocking = True

        return {
            "scores": scores,
            "suggestions": suggestions,
            "blocking": blocking,
            "critic_type": "llm",
            "fallback_reason": None,
        }


# ============================================================
# Benchmark utility
# ============================================================

def benchmark(model: CriticModel, n_runs: int = 5) -> dict[str, Any]:
    """Run benchmark against a CriticModel and return stats."""
    import time

    dummy_output = {"command": "az vm show --name test --resource-group test --output json", "exit_code": 0, "stdout": "{}", "stderr": ""}
    dummy_rubric = {
        "correctness": {"threshold": 0.5},
        "safety": {"threshold": 1.0},
        "idempotency": {"threshold": 0.5},
        "traceability": {"threshold": 0.5},
        "spec_compliance": {"threshold": 0.5},
    }
    dummy_trace = {"iterations": []}

    latencies: list[float] = []
    tokens: list[int] = []
    for _ in range(n_runs):
        start = time.perf_counter()
        _ = model.score(dummy_output, dummy_rubric, dummy_trace)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)
        # Token estimate: 1 token ≈ 4 chars for English
        prompt = _build_critic_prompt(dummy_output, dummy_rubric, dummy_trace)
        tokens.append(len(prompt) // 4)

    avg_latency = sum(latencies) / len(latencies)
    avg_tokens = sum(tokens) / len(tokens)

    return {
        "avg_tokens": round(avg_tokens),
        "avg_latency_ms": round(avg_latency, 1),
        "n_runs": n_runs,
        "min_latency_ms": round(min(latencies), 1),
        "max_latency_ms": round(max(latencies), 1),
    }
