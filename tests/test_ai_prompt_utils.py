"""Tests for AI prompt utilities."""

# pylint: disable=missing-function-docstring,missing-class-docstring,unused-argument,duplicate-code

import asyncio
from echo_journal import ai_prompt_utils as ai


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
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert asyncio.run(ai.fetch_ai_prompt()) is None


def test_fetch_ai_prompt(monkeypatch):
    """Valid responses should return structured prompt data."""
    payload = {"choices": [{"text": '{"prompt": "Hello", "anchor": "soft", "tags": ["mood"]}' }]}  # noqa: E501
    client = FakeClient(payload)
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda: client)

    data = asyncio.run(ai.fetch_ai_prompt())

    assert data == {"prompt": "Hello", "anchor": "soft", "tags": ["mood"]}
    assert client.captured["url"] == ai.OPENAI_URL
    assert client.captured["headers"]["Authorization"] == "Bearer x"
