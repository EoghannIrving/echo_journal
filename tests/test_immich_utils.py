"""Tests for Immich API utilities."""

import asyncio
import json as jsonlib

from echo_journal import immich_utils


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
    assert client.captured["json"]["takenAfter"] == "2025-07-18T09:00:00Z"
    assert client.captured["json"]["takeBefore"] == "2025-07-20T14:59:59Z"


def test_update_photo_metadata_filters_assets(monkeypatch, tmp_path):
    """Only assets matching the journal date should be saved."""

    assets = [
        {
            "id": "a1",
            "originalFileName": "in-range.jpg",
            "fileCreatedAt": "2025-07-19T10:00:00Z",
        },
        {
            "id": "a2",
            "originalFileName": "too-early.jpg",
            "fileCreatedAt": "2025-07-18T23:59:00Z",
        },
        {
            "id": "a3",
            "originalFileName": "too-late.jpg",
            "fileCreatedAt": "2025-07-20T00:00:00Z",
        },
    ]

    async def fake_fetch(_date, media_type="IMAGE"):
        _ = media_type
        return assets

    monkeypatch.setattr(immich_utils, "fetch_assets_for_date", fake_fetch)

    md_path = tmp_path / "2025-07-19.md"
    md_path.write_text("x", encoding="utf-8")

    asyncio.run(immich_utils.update_photo_metadata("2025-07-19", md_path))

    json_path = md_path.with_suffix(".photos.json")
    data = jsonlib.loads(json_path.read_text(encoding="utf-8"))

    assert len(data) == 1
    assert data[0]["caption"] == "in-range.jpg"
