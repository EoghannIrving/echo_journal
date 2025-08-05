"""Tests for AI prompt utilities."""

# pylint: disable=missing-function-docstring,missing-class-docstring,unused-argument,duplicate-code

import asyncio

from echo_journal import ai_prompt_utils as ai
from echo_journal import config


class FakeClient:
    """Fake ``httpx.AsyncClient`` for testing."""

    def __init__(self, data):
        self._data = data
        self.captured = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None, timeout=None):
        self.captured["url"] = url
        self.captured["headers"] = headers
        self.captured["json"] = json

        class Response:
            def __init__(self, data):
                self._data = data

            def raise_for_status(self):
                return None

            def json(self):
                return self._data

        return Response(self._data)


def test_no_api_key(monkeypatch):
    """When no API key is set, ``fetch_ai_prompt`` returns ``None``."""
    monkeypatch.setattr(config, "OPENAI_API_KEY", None)
    assert asyncio.run(ai.fetch_ai_prompt("soft")) is None


def test_fetch_ai_prompt(monkeypatch):
    """Valid responses should return parsed prompt dict."""
    yaml_str = "- id: tag-001\n  prompt: Hi\n  tags:\n    - mood\n  anchor: soft"
    client = FakeClient(
        {"choices": [{"message": {"content": [{"type": "text", "text": yaml_str}]}}]}
    )
    monkeypatch.setattr(config, "OPENAI_API_KEY", "x")
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda: client)

    prompt = asyncio.run(ai.fetch_ai_prompt("soft"))

    assert prompt == {"id": "tag-001", "prompt": "Hi", "tags": ["mood"], "anchor": "soft"}
    assert client.captured["url"] == ai.CHAT_URL
    assert client.captured["headers"]["Authorization"] == "Bearer x"
    assert client.captured["json"]["model"] == "gpt-4o-mini"
    assert client.captured["json"]["max_tokens"] == 300
    assert "soft" in client.captured["json"]["messages"][0]["content"]


def test_fetch_ai_prompt_string_content(monkeypatch):
    """String responses from older APIs should also work."""
    yaml_str = "- id: tag-001\n  prompt: Hi\n  tags:\n    - mood\n  anchor: soft"
    client = FakeClient({"choices": [{"message": {"content": yaml_str}}]})
    monkeypatch.setattr(config, "OPENAI_API_KEY", "x")
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda: client)

    prompt = asyncio.run(ai.fetch_ai_prompt("soft"))

    assert prompt["prompt"] == "Hi"


def test_fetch_ai_prompt_from_settings(monkeypatch):
    """API key provided via settings.yaml should be used."""
    yaml_str = "- id: tag-001\n  prompt: Hi\n  tags:\n    - mood\n  anchor: soft"
    client = FakeClient(
        {"choices": [{"message": {"content": [{"type": "text", "text": yaml_str}]}}]}
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(config, "_SETTINGS", {"OPENAI_API_KEY": "from_settings"})
    monkeypatch.setattr(config, "OPENAI_API_KEY", config._get_setting("OPENAI_API_KEY"))
    monkeypatch.setattr(ai, "config", config)
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda: client)

    prompt = asyncio.run(ai.fetch_ai_prompt("soft"))

    assert prompt["prompt"] == "Hi"
    assert client.captured["headers"]["Authorization"] == "Bearer from_settings"


def test_fetch_ai_prompt_code_fence(monkeypatch):
    """YAML wrapped in code fences should be parsed correctly."""
    yaml_str = "- id: tag-001\n  prompt: Hi\n  tags:\n    - mood\n  anchor: soft"
    fenced = f"```yaml\n{yaml_str}\n```"
    client = FakeClient({"choices": [{"message": {"content": [{"type": "text", "text": fenced}]}}]})
    monkeypatch.setattr(config, "OPENAI_API_KEY", "x")
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda: client)

    prompt = asyncio.run(ai.fetch_ai_prompt("soft"))

    assert prompt["prompt"] == "Hi"
