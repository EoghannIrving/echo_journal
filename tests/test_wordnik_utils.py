"""Tests for Wordnik utilities."""

# pylint: disable=missing-function-docstring,missing-class-docstring,unused-argument,duplicate-code

import asyncio

import wordnik_utils as wu


class FakeClient:
    """Minimal async client for ``httpx.AsyncClient``."""

    def __init__(self, data):
        self._data = data
        self.captured = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None, timeout=None):
        self.captured["url"] = url
        self.captured["params"] = params

        class Response:
            def __init__(self, data):
                self._data = data

            def raise_for_status(self):
                return None

            def json(self):
                return self._data

        return Response(self._data)


def test_no_api_key(monkeypatch):
    """Missing API key should return ``None``."""
    monkeypatch.delenv("WORDNIK_API_KEY", raising=False)
    assert asyncio.run(wu.fetch_word_of_day()) is None


def test_fetch_word_of_day(monkeypatch):
    """Valid responses should return word and definition."""
    client = FakeClient({"word": "apple", "definitions": [{"text": "a fruit"}]})
    monkeypatch.setenv("WORDNIK_API_KEY", "k")
    monkeypatch.setattr(wu.httpx, "AsyncClient", lambda: client)

    result = asyncio.run(wu.fetch_word_of_day())

    assert result == ("apple", "a fruit")
    assert client.captured["params"]["api_key"] == "k"
