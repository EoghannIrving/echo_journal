"""Tests for Activation Engine utilities."""

# pylint: disable=duplicate-code

import asyncio

import activation_engine_utils as ae


class FakeClient:
    """Minimal async client to capture POST requests."""

    def __init__(self, data):
        """Initialize the client with ``data`` to return from responses."""
        self._data = data
        self.captured = {}

    async def __aenter__(self):
        """Enter the async context manager returning ``self``."""
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Exit the async context manager."""
        return False

    async def post(self, url, json=None, timeout=None):
        """Capture POST ``url`` and ``json`` payloads and return a stubbed response."""
        self.captured["url"] = url
        self.captured["json"] = json
        self.captured["timeout"] = timeout

        class Response:
            """Simple response object mimicking an ``httpx`` response."""

            def __init__(self, data):
                """Store ``data`` for later retrieval."""
                self._data = data

            def raise_for_status(self):
                """No-op ``raise_for_status`` implementation."""
                return None

            def json(self):
                """Return the stored ``data``."""
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
