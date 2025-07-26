"""Tests for Jellyfin API utilities."""

import asyncio

import jellyfin_utils


class FakeClient:
    """Simplified ``httpx.AsyncClient`` mock for ``fetch_top_songs``."""

    def __init__(self) -> None:
        """Initialize the fake client with a blank ``url`` attribute."""
        self.url = ""

    def __init__(self, items=None):
        self.items = items

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None, params=None, timeout=None):
        """Store request info and return a mock response."""
        _ = headers
        _ = params
        _ = timeout
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

        default_items = [
        items = [
            {
                "Name": "Song1",
                "ArtistItems": [{"Name": "Artist1"}],
                "UserData": {"LastPlayedDate": "2025-07-25T12:00:00Z"},
            },
            {
                "Name": "Song1",
                "ArtistItems": [{"Name": "Artist1"}],
                "UserData": {"LastPlayedDate": "2025-07-25T13:00:00Z"},
            },
            {
                "Name": "Song2",
                "ArtistItems": [{"Name": "Artist2"}],
                "UserData": {"LastPlayedDate": "2025-07-24T11:00:00Z"},
            },
        ]
        items = self.items or default_items
        return Response(items)


def test_fetch_top_songs_lastplayed(monkeypatch):
    """Items using LastPlayedDate should be counted."""
    client = FakeClient()
    monkeypatch.setattr(jellyfin_utils.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(jellyfin_utils, "JELLYFIN_URL", "http://example")
    monkeypatch.setattr(jellyfin_utils, "JELLYFIN_USER_ID", "uid")

    songs = asyncio.run(jellyfin_utils.fetch_top_songs("2025-07-25"))

    assert songs[0]["track"] == "Song1"
    assert songs[0]["artist"] == "Artist1"
    assert songs[0]["plays"] == 2


def test_fetch_top_songs_tiebreak(monkeypatch):
    """Songs with equal plays should sort alphabetically."""
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

    assert songs[0]["track"] == "Alpha"
    assert songs[1]["track"] == "Beta"
