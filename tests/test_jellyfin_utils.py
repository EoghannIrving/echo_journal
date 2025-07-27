"""Tests for Jellyfin API utilities."""

import asyncio

import jellyfin_utils


class FakeClient:
    """Simplified ``httpx.AsyncClient`` mock for ``fetch_top_songs``."""

    def __init__(self, items=None) -> None:
        """Initialize the fake client."""
        self.url = ""
        self.calls = []
        self.items = items

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None, params=None, timeout=None):
        """Store request info and return a mock response."""
        _ = headers
        _ = timeout
        self.calls.append(params)
        self.url = url

        class Response:
            """Minimal ``httpx.Response`` stand-in."""

            def __init__(self, items):
                self._items = items

            def raise_for_status(self):
                """Pretend the request succeeded."""
                return None

            def json(self):
                """Return the payload in ``httpx`` style."""
                return {"Items": self._items}
        if self.items is not None:
            items = self.items
        else:
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


def test_fetch_top_songs_tiebreak(monkeypatch):
    """Songs with equal plays should sort by most recent play."""
    items = [
        {
            "Name": "Beta",
            "ArtistItems": [{"Name": "ArtistB"}],
            "UserData": {"LastPlayedDate": "2025-07-25T14:00:00Z"},
        },
        {
            "Name": "Alpha",
            "ArtistItems": [{"Name": "ArtistA"}],
            "UserData": {"LastPlayedDate": "2025-07-25T13:00:00Z"},
        },
        {
            "Name": "Alpha",
            "ArtistItems": [{"Name": "ArtistA"}],
            "UserData": {"LastPlayedDate": "2025-07-25T12:00:00Z"},
        },
        {
            "Name": "Beta",
            "ArtistItems": [{"Name": "ArtistB"}],
            "UserData": {"LastPlayedDate": "2025-07-25T11:00:00Z"},
        },
    ]

    client = FakeClient(items)
    monkeypatch.setattr(jellyfin_utils.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(jellyfin_utils, "JELLYFIN_URL", "http://example")
    monkeypatch.setattr(jellyfin_utils, "JELLYFIN_USER_ID", "uid")

    songs = asyncio.run(jellyfin_utils.fetch_top_songs("2025-07-25"))

    assert songs[0]["track"] == "Beta"
    assert songs[1]["track"] == "Alpha"


def test_fetch_top_songs_threshold(monkeypatch):
    """Songs below the playback threshold should be ignored."""
    items = [
        {
            "Name": "SkipMe",
            "ArtistItems": [{"Name": "ArtistS"}],
            "UserData": {
                "LastPlayedDate": "2025-07-25T10:00:00Z",
                "PlayedPercentage": 50,
            },
        },
        {
            "Name": "KeepMe",
            "ArtistItems": [{"Name": "ArtistK"}],
            "UserData": {
                "LastPlayedDate": "2025-07-25T09:00:00Z",
                "PlayedPercentage": 95,
            },
        },
    ]

    client = FakeClient(items)
    monkeypatch.setattr(jellyfin_utils.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(jellyfin_utils, "JELLYFIN_URL", "http://example")
    monkeypatch.setattr(jellyfin_utils, "JELLYFIN_USER_ID", "uid")

    songs = asyncio.run(jellyfin_utils.fetch_top_songs("2025-07-25"))

    assert len(songs) == 1
    assert songs[0]["track"] == "KeepMe"
