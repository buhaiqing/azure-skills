"""P1-T1.2-1: Fallback test — LLM API HTTP error (500, timeout, etc.)

Covers: _call_llm() raises → score() falls back to rule-based critic.
"""

import json
import sys

import pytest

sys.path.insert(0, "scripts")


def test_llm_call_http_error_fallback(monkeypatch):
    """When _call_llm raises an exception (HTTP error), score() must fallback."""
    from llm_critic import CriticModel

    # Step 1: inject a fake API key so _can_call_llm() returns True
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")

    # Step 2: monkeypatch _call_llm to always raise
    monkeypatch.setattr(CriticModel, "_call_llm", lambda self, prompt: (_ for _ in ()).throw(
        ConnectionError("Simulated HTTP 500 from api.openai.com")
    ))

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = model.score(
        generator_output={"command": "az vm show --name test --resource-group test --output json",
                          "exit_code": 0, "stdout": "{}", "stderr": ""},
        rubric={"correctness": {"threshold": 0.5}, "safety": {"threshold": 1.0},
                "idempotency": {"threshold": 0.5}, "traceability": {"threshold": 0.5},
                "spec_compliance": {"threshold": 0.5}},
        trace={"iterations": []},
    )

    # 验收标准
    assert result["critic_type"] == "rule_based", "HTTP error → must fallback to rule-based"
    assert "LLM call failed" in result.get("fallback_reason", ""), \
        f"fallback_reason should indicate LLM failure, got: {result.get('fallback_reason')}"
    assert "scores" in result
    assert "blocking" in result


def test_llm_call_timeout_fallback(monkeypatch):
    """When _call_llm times out, score() must fallback to rule-based."""
    from llm_critic import CriticModel

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")

    def _raise_timeout(self, prompt):
        import socket
        raise socket.timeout("Simulated read timeout after 30s")

    monkeypatch.setattr(CriticModel, "_call_llm", _raise_timeout)

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = model.score(
        generator_output={"command": "az aks list", "exit_code": 0, "stdout": "[]", "stderr": ""},
        rubric={"correctness": {"threshold": 0.5}},
        trace={"iterations": []},
    )

    assert result["critic_type"] == "rule_based"


def test_llm_call_rate_limit_fallback(monkeypatch):
    """When _call_llm hits a 429 rate limit, score() must fallback."""
    from llm_critic import CriticModel

    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")

    def _raise_429(self, prompt):
        import urllib.error
        raise urllib.error.HTTPError(
            url="https://api.anthropic.com/v1/messages",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=None,
        )

    monkeypatch.setattr(CriticModel, "_call_llm", _raise_429)

    model = CriticModel(provider="anthropic", model_name="claude-3-haiku-20240307")
    result = model.score(
        generator_output={"command": "az blob list", "exit_code": 0, "stdout": "[]", "stderr": ""},
        rubric={"correctness": {"threshold": 0.5}},
        trace={"iterations": []},
    )

    assert result["critic_type"] == "rule_based"
    assert "scores" in result
    assert isinstance(result["blocking"], bool)
