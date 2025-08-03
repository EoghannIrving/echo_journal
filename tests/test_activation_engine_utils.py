"""Tests for Activation Engine utilities."""

import asyncio

import activation_engine_utils as ae


class FakeClient:
    """Minimal async client to capture POST requests."""

    def __init__(self, data):
        self._data = data
        self.captured = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, timeout=None):
        self.captured["url"] = url
        self.captured["json"] = json

        class Response:
            def __init__(self, data):
                self._data = data

            def raise_for_status(self):
                return None

            def json(self):
                return self._data

        return Response(self._data)


def test_fetch_tags(monkeypatch):
    """``fetch_tags`` should POST data and return strings."""
    client = FakeClient({"tags": ["joy", 1, "calm"]})
    monkeypatch.setattr(ae.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(ae, "ACTIVATION_ENGINE_URL", "http://ae")

    tags = asyncio.run(ae.fetch_tags("m", "e", "ctx"))

    assert tags == ["joy", "1", "calm"]
    assert client.captured["url"] == "http://ae/get-tags"
    assert client.captured["json"]["mood"] == "m"


def test_rank_prompts(monkeypatch):
    """``rank_prompts`` should return prompts ordered by relevance."""
    client = FakeClient({"candidates": [{"task": "b"}, {"task": "a"}]})
    monkeypatch.setattr(ae.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(ae, "ACTIVATION_ENGINE_URL", "http://ae")

    ranked = asyncio.run(ae.rank_prompts(["a", "b"], ["joy"]))

    assert ranked == ["b", "a"]
    assert client.captured["url"] == "http://ae/rank-tasks"
    assert client.captured["json"]["user_state"]["mood"] == "joy"
