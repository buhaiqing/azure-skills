"""TDD tests for llm_critic.py — LLM-powered GCL Critic.

These tests define the CONTRACT for llm_critic.py before implementation.
All tests start as RED (import error or AssertionError) and turn GREEN as the module is built.
"""

import json
import sys

import pytest

sys.path.insert(0, "scripts")


# ============================================================
# Test 1: Module should be importable
# ============================================================

def test_llm_critic_module_importable():
    """Module `scripts/llm_critic.py` must exist and be importable."""
    try:
        import llm_critic  # noqa: F401
    except ImportError:
        pytest.fail("llm_critic module is not yet created")


# ============================================================
# Test 2: CriticModel abstraction — 3 providers
# ============================================================

def test_critic_model_provider_selection():
    """Must support 'openai', 'azure_openai', 'anthropic', 'qwen' as valid providers."""
    from llm_critic import CriticModel

    # Valid providers
    for provider in ["openai", "azure_openai", "anthropic", "qwen"]:
        model = CriticModel(provider=provider, model_name="test")
        assert model.provider == provider

    # Invalid provider
    with pytest.raises(ValueError, match="Unsupported provider"):
        CriticModel(provider="gemini", model_name="test")


# ============================================================
# Test 3: Fallback to rule-based critic when no API key
# ============================================================

def test_critic_model_fallback_when_no_api_key(monkeypatch):
    """When API key is missing, must fallback to rule-based scoring."""
    from llm_critic import CriticModel

    # Remove all LLM API keys
    for env_var in ["OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DASHSCOPE_API_KEY"]:
        monkeypatch.delenv(env_var, raising=False)

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = model.score(
        generator_output={"command": "az vm show", "exit_code": 0, "stdout": "{}", "stderr": ""},
        rubric={"correctness": {"threshold": 0.5}},
        trace={"iterations": []},
    )
    assert "scores" in result
    assert result.get("critic_type") == "rule_based", "Should fallback to rule-based"
    assert result.get("fallback_reason") is not None


# ============================================================
# Test 4: LLM Critic score format
# ============================================================

def test_critic_model_score_format():
    """Score output must conform to AGENTS.md §7 contract."""
    from llm_critic import CriticModel

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")

    # Even in dry-run / fallback, the output must match the contract
    result = model.score(
        generator_output={"command": "az vm create", "exit_code": 0, "stdout": "created", "stderr": ""},
        rubric={
            "correctness": {"threshold": 0.5},
            "safety": {"threshold": 1.0},
            "idempotency": {"threshold": 0.5},
            "traceability": {"threshold": 0.5},
            "spec_compliance": {"threshold": 0.5},
        },
        trace={"iterations": []},
    )

    # Required contract fields
    assert "scores" in result
    assert "suggestions" in result
    assert "blocking" in result
    assert isinstance(result["blocking"], bool)

    # Scores must cover all 5 rubric dimensions
    for dim in ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]:
        assert dim in result["scores"], f"Missing dimension: {dim}"
        assert result["scores"][dim] in [0, 0.5, 1], f"Invalid score for {dim}: {result['scores'][dim]}"


# ============================================================
# Test 5: Safety=0 forces blocking=True
# ============================================================

def test_safety_zero_forces_blocking():
    """When safety=0, blocking MUST be True regardless of other scores."""
    from llm_critic import CriticModel

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")

    result = model.score(
        generator_output={
            "command": "az vm delete --name myvm --resource-group myrg",
            "exit_code": 0,
            "stdout": "AZURE_CLIENT_SECRET=abc123",  # credential leak → safety 0
            "stderr": "",
        },
        rubric={
            "correctness": {"threshold": 0.5},
            "safety": {"threshold": 1.0},
            "idempotency": {"threshold": 0.5},
            "traceability": {"threshold": 0.5},
            "spec_compliance": {"threshold": 0.5},
        },
        trace={"iterations": []},
    )

    if result["scores"]["safety"] == 0:
        assert result["blocking"] is True, "Safety=0 MUST force blocking=True"


# ============================================================
# Test 6: Critic must NOT see user request
# ============================================================

def test_critic_never_receives_user_request():
    """AGENTS.md §7: Critic prompt must hide raw user request to prevent rubber-stamping."""
    from llm_critic import CriticModel

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")

    # The API must NOT have a `user_request` parameter
    sig = model.score.__code__.co_varnames
    assert "user_request" not in sig, "Critic.score() must NOT accept user_request parameter"


# ============================================================
# Test 7: Token-efficient prompt (no multi-level nesting)
# ============================================================

def test_llm_prompt_structure_no_nesting():
    """Prompt must be flat-structured to avoid JSON reparsing by LLM."""
    from llm_critic import _build_critic_prompt

    prompt = _build_critic_prompt(
        generator_output={"command": "az vm list", "exit_code": 0, "stdout": "[]"},
        rubric={"correctness": {"threshold": 0.5}},
        trace={"iterations": []},
    )

    # Prompt must be a string
    assert isinstance(prompt, str)

    # Must NOT contain nested JSON inside JSON (anti-pattern)
    assert prompt.count('{') < 10, "Prompt too nested — LLMs lose structure in deeply nested JSON"

    # Must contain rubric section header
    assert "rubric" in prompt.lower() or "Rubric" in prompt or "RUBRIC" in prompt

    # Must contain generator_output content
    assert "az vm list" in prompt or "az" in prompt


# ============================================================
# Test 8: Benchmark capability
# ============================================================

def test_benchmark_returns_stats(monkeypatch):
    """benchmark() must return avg_tokens and avg_latency."""
    from llm_critic import benchmark, CriticModel

    # Disable real API calls for benchmark test
    monkeypatch.setattr(CriticModel, "_call_llm", lambda self, prompt: json.dumps({
        "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1},
        "suggestions": [],
        "blocking": False,
    }))

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = benchmark(model, n_runs=2)  # minimal runs for test speed

    assert "avg_tokens" in result
    assert "avg_latency_ms" in result
    assert "n_runs" in result
    assert result["n_runs"] == 2
