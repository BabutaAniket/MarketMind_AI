from types import SimpleNamespace

import litellm
import pytest
from openai import OpenAIError

from marketmind.llm_client import chat


def test_ollama_chat_uses_litellm_route_and_json_mode(monkeypatch):
    seen = {}

    def fake_completion(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":true}'))])

    monkeypatch.setattr(litellm, "completion", fake_completion)
    result = chat([{"role": "user", "content": "test"}], json_mode=True)
    assert result == '{"ok":true}'
    assert seen["model"] == "ollama_chat/qwen3:4b"
    assert seen["api_base"] == "http://localhost:11434"
    assert seen["response_format"] == {"type": "json_object"}


def test_openrouter_requires_explicit_credentials(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        chat([{"role": "user", "content": "test"}], provider="openrouter")


def test_provider_failures_are_reported_without_fallback(monkeypatch):
    def fail(**kwargs):
        raise OpenAIError("model server unavailable")

    monkeypatch.setattr(litellm, "completion", fail)
    with pytest.raises(RuntimeError, match="model server unavailable"):
        chat([{"role": "user", "content": "test"}])
