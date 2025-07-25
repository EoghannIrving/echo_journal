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
        self.captured["url"] = url
        self.captured["json"] = json

        class Response:
            @staticmethod
            def raise_for_status():
                pass

            @staticmethod
            def json():
                return []

        return Response()


def test_fetch_assets_posts_search(monkeypatch):
    """``fetch_assets_for_date`` should POST to ``asset/search`` with payload."""

    client = FakeClient()
    monkeypatch.setattr(immich_utils.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(immich_utils, "IMMICH_URL", "http://example/api")

    asyncio.run(immich_utils.fetch_assets_for_date("2025-07-19"))

    assert client.captured["url"] == "http://example/api/asset/search"
    assert client.captured["json"]["createdAt"]["min"] == "2025-07-19T00:00:00Z"
    assert client.captured["json"]["createdAt"]["max"] == "2025-07-19T23:59:59Z"
