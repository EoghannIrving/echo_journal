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
    assert asyncio.run(ai.fetch_ai_prompt()) is None


def test_fetch_ai_prompt(monkeypatch):
    """Valid responses should return trimmed prompt text."""
    client = FakeClient({"choices": [{"text": "  Hello\n"}]})
    monkeypatch.setattr(config, "OPENAI_API_KEY", "x")
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda: client)

    prompt = asyncio.run(ai.fetch_ai_prompt())

    assert prompt == "Hello"
    assert client.captured["url"] == ai.OPENAI_URL
    assert client.captured["headers"]["Authorization"] == "Bearer x"


def test_fetch_ai_prompt_from_settings(monkeypatch):
    """API key provided via settings.yaml should be used."""
    client = FakeClient({"choices": [{"text": "Hi"}]})
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(config, "_SETTINGS", {"OPENAI_API_KEY": "from_settings"})
    monkeypatch.setattr(config, "OPENAI_API_KEY", config._get_setting("OPENAI_API_KEY"))
    monkeypatch.setattr(ai, "config", config)
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda: client)

    prompt = asyncio.run(ai.fetch_ai_prompt())

    assert prompt == "Hi"
    assert client.captured["headers"]["Authorization"] == "Bearer from_settings"
