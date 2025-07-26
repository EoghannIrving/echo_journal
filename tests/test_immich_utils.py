"""Tests for Immich API utilities."""

import asyncio

import immich_utils


class FakeClient:
    """Simple mock of ``httpx.AsyncClient`` to capture requests."""

    def __init__(self):
        self.captured = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None, timeout=None):
        """Record POST data and return a simple response object."""
        _ = headers  # parameters kept for API parity
        _ = timeout
        self.captured["url"] = url
        self.captured["json"] = json

        class Response:
            """Bare-minimum response object for tests."""

            @staticmethod
            def raise_for_status():
                """Pretend the response was successful."""
                return None

            @staticmethod
            def json():
                """Return an empty payload like ``httpx.Response.json``."""
                return []

        return Response()


def test_fetch_assets_posts_search(monkeypatch):
    """``fetch_assets_for_date`` should POST to ``asset/search`` with payload."""

    client = FakeClient()
    monkeypatch.setattr(immich_utils.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(immich_utils, "IMMICH_URL", "http://example/api")

    asyncio.run(immich_utils.fetch_assets_for_date("2025-07-19"))

    assert client.captured["url"] == "http://example/api/search/metadata"
    assert client.captured["json"]["createdAfter"] == "2025-07-19T00:00:00Z"
    assert client.captured["json"]["createdBefore"] == "2025-07-19T23:59:59Z"
