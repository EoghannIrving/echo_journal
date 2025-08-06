"""Tests for number fact utilities."""

# pylint: disable=missing-function-docstring,missing-class-docstring,unused-argument,duplicate-code

import asyncio
from datetime import date

from echo_journal import numbers_utils as nu


class FakeClient:
    """Minimal ``httpx.AsyncClient`` stand-in."""

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


def test_fetch_date_fact(monkeypatch):
    """The request should hit the useless facts API with language parameter."""
    client = FakeClient({"text": "a fact"})
    monkeypatch.setattr(nu.httpx, "AsyncClient", lambda: client)

    result = asyncio.run(nu.fetch_date_fact(date(2024, 1, 2)))

    assert result == "a fact"
    assert client.captured["url"] == "https://uselessfacts.jsph.pl/api/v2/facts/random"
    assert client.captured["params"] == {"language": "en"}
