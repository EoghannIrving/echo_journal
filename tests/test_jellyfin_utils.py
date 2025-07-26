"""Tests for Jellyfin API utilities."""

import asyncio

import jellyfin_utils


class FakeClient:
    """Simplified httpx.AsyncClient mock for fetch_top_songs."""

    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None, params=None, timeout=None):
        _ = headers
        _ = timeout
        self.calls.append(params)
        self.url = url
        class Response:
            def __init__(self, items):
                self._items = items
            def raise_for_status(self):
                return None
            def json(self):
                return {"Items": self._items}
        start = int(params.get("StartIndex", 0))
        limit = int(params.get("Limit", 0))
        if start < 4:
            items = [
                {
                    "Name": "Song1",
                    "ArtistItems": [{"Name": "Artist1"}],
                    "UserData": {"LastPlayedDate": "2025-07-25T12:00:00Z"},
                }
                for _ in range(limit)
            ]
        else:
            items = [
                {
                    "Name": "Song2",
                    "ArtistItems": [{"Name": "Artist2"}],
                    "UserData": {"LastPlayedDate": "2025-07-24T11:00:00Z"},
                }
            ]
        return Response(items)


def test_fetch_top_songs_lastplayed(monkeypatch):
    """Items using LastPlayedDate should be counted."""
    client = FakeClient()
    monkeypatch.setattr(jellyfin_utils.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(jellyfin_utils, "JELLYFIN_URL", "http://example")
    monkeypatch.setattr(jellyfin_utils, "JELLYFIN_USER_ID", "uid")
    monkeypatch.setattr(jellyfin_utils, "JELLYFIN_PAGE_SIZE", 2)

    songs = asyncio.run(jellyfin_utils.fetch_top_songs("2025-07-25"))

    assert songs[0]["track"] == "Song1"
    assert songs[0]["artist"] == "Artist1"
    assert songs[0]["plays"] == 4
    assert len(client.calls) == 3
