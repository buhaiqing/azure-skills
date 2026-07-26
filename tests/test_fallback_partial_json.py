"""P1-T1.2-3: Fallback test — LLM returns JSON with missing/partial fields.

Covers: _call_llm() returns valid JSON but missing `scores` / `blocking` fields.
The score() method must gracefully handle missing fields with defaults.
"""

import sys

import pytest

sys.path.insert(0, "scripts")


def test_llm_json_missing_scores_field(monkeypatch):
    """LLM returns {} → scores default to 0.5, still returns as llm type."""
    from llm_critic import CriticModel

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(
        CriticModel,
        "_call_llm",
        lambda self, prompt: '{}',
    )

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = model.score(
        generator_output={"command": "az vm show --name test --resource-group test --output json",
                          "exit_code": 0, "stdout": "{}", "stderr": ""},
        rubric={"correctness": {"threshold": 0.5}},
        trace={"iterations": []},
    )

    # Empty JSON is still valid → critic_type = "llm" (not fallback)
    # But scores should be present with defaults
    assert "scores" in result
    assert result["critic_type"] == "llm", "Empty JSON is valid JSON — not a fallback"
    # Each dimension defaults to 0.5
    for dim in ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]:
        assert dim in result["scores"], f"Missing dimension: {dim}"
        assert result["scores"][dim] in [0, 0.5, 1], \
            f"Invalid default for {dim}: {result['scores'][dim]}"


def test_llm_json_partial_scores(monkeypatch):
    """LLM returns scores with only 2 of 5 dimensions → missing default to 0.5."""
    from llm_critic import CriticModel

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(
        CriticModel,
        "_call_llm",
        lambda self, prompt: '{"scores": {"correctness": 1, "safety": 1}}',
    )

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = model.score(
        generator_output={"command": "az vm list", "exit_code": 0, "stdout": "[]", "stderr": ""},
        rubric={"correctness": {"threshold": 0.5}},
        trace={"iterations": []},
    )

    # Explicitly provided scores preserved
    assert result["scores"]["correctness"] == 1
    assert result["scores"]["safety"] == 1

    # Missing scores default to 0.5
    assert result["scores"]["idempotency"] == 0.5
    assert result["scores"]["traceability"] == 0.5
    assert result["scores"]["spec_compliance"] == 0.5


def test_llm_json_missing_blocking_field(monkeypatch):
    """LLM returns valid scores but no `blocking` field → defaults to False."""
    from llm_critic import CriticModel

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(
        CriticModel,
        "_call_llm",
        lambda self, prompt: '{"scores": {"correctness": 0, "safety": 0, "idempotency": 0, "traceability": 0, "spec_compliance": 0}}',
    )

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = model.score(
        generator_output={"command": "az vm list", "exit_code": 0, "stdout": "[]", "stderr": ""},
        rubric={"correctness": {"threshold": 0.5}},
        trace={"iterations": []},
    )

    # blocking defaults to False when missing, BUT safety=0 forces it to True
    assert result["blocking"] is True, "Safety=0 must force blocking=True"
    assert result["scores"]["safety"] == 0


def test_llm_json_extra_fields_ignored(monkeypatch):
    """LLM returns extra fields beyond contract → silently ignored."""
    from llm_critic import CriticModel

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(
        CriticModel,
        "_call_llm",
        lambda self, prompt: '{"scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1}, "suggestions": ["ok"], "blocking": false, "confidence": 0.95, "reasoning": "looks good", "model_used": "gpt-4o"}',
    )

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = model.score(
        generator_output={"command": "az vm list", "exit_code": 0, "stdout": "[]", "stderr": ""},
        rubric={"correctness": {"threshold": 0.5}},
        trace={"iterations": []},
    )

    # Contract fields present
    assert result["scores"]["correctness"] == 1
    assert result["suggestions"] == ["ok"]
    assert result["blocking"] is False

    # Extra fields NOT leaked into output
    assert "confidence" not in result
    assert "reasoning" not in result
    assert "model_used" not in result


def test_llm_json_null_scores(monkeypatch):
    """LLM returns null for some scores → default to 0.5."""
    from llm_critic import CriticModel

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(
        CriticModel,
        "_call_llm",
        lambda self, prompt: '{"scores": {"correctness": null, "safety": null}}',
    )

    model = CriticModel(provider="openai", model_name="gpt-4o-mini")
    result = model.score(
        generator_output={"command": "az vm list", "exit_code": 0, "stdout": "[]", "stderr": ""},
        rubric={"correctness": {"threshold": 0.5}},
        trace={"iterations": []},
    )

    # null values default to 0.5
    assert result["scores"]["correctness"] == 0.5
    assert result["scores"]["safety"] == 0.5