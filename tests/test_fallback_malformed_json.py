"""P1-T1.2-2: Fallback test — LLM returns malformed JSON.

Covers: _call_llm() returns text that is not valid JSON → score() falls back.
"""

import sys

import pytest

sys.path.insert(0, "scripts")


def test_llm_returns_plain_text_not_json(monkeypatch):
    """LLM returns "I cannot score this" → json.loads() fails → fallback."""
    from llm_critic import CriticModel

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(
        CriticModel,
        "_call_llm",
        lambda self, prompt: "I'm sorry, I cannot process this request right now. Please try again later.",
    )

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = model.score(
        generator_output={"command": "az vm show --name test --resource-group test --output json",
                          "exit_code": 0, "stdout": "{}", "stderr": ""},
        rubric={"correctness": {"threshold": 0.5}},
        trace={"iterations": []},
    )

    assert result["critic_type"] == "rule_based", "Plain text → must fallback"
    assert "LLM call failed" in result.get("fallback_reason", "")


def test_llm_returns_json_with_code_fence(monkeypatch):
    """LLM wraps JSON in ```json``` code fence — should be treated as invalid JSON."""
    from llm_critic import CriticModel

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(
        CriticModel,
        "_call_llm",
        lambda self, prompt: '```json\n{"scores": {"correctness": 1}}\n```',
    )

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = model.score(
        generator_output={"command": "az vm list", "exit_code": 0, "stdout": "[]", "stderr": ""},
        rubric={"correctness": {"threshold": 0.5}},
        trace={"iterations": []},
    )

    # Code-fence-wrapped JSON is NOT valid JSON → must fallback
    assert result["critic_type"] == "rule_based"


def test_llm_returns_xml_not_json(monkeypatch):
    """LLM hallucinates XML output → fallback."""
    from llm_critic import CriticModel

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(
        CriticModel,
        "_call_llm",
        lambda self, prompt: '<response><scores><correctness>1</correctness></scores></response>',
    )

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = model.score(
        generator_output={"command": "az vm list", "exit_code": 0, "stdout": "[]", "stderr": ""},
        rubric={"correctness": {"threshold": 0.5}},
        trace={"iterations": []},
    )

    assert result["critic_type"] == "rule_based"


def test_llm_returns_empty_string(monkeypatch):
    """LLM returns empty string → fallback."""
    from llm_critic import CriticModel

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(CriticModel, "_call_llm", lambda self, prompt: "")

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = model.score(
        generator_output={"command": "az vm list", "exit_code": 0, "stdout": "[]", "stderr": ""},
        rubric={"correctness": {"threshold": 0.5}},
        trace={"iterations": []},
    )

    assert result["critic_type"] == "rule_based"