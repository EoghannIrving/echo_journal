"""Tests for AudioBookShelf integration utilities."""

import asyncio

from echo_journal import audiobookshelf_utils as abs_utils


class FakeClient:
    """Stub AsyncClient that yields predictable ABS payloads."""

    def __init__(self, me_payload=None, item_payload=None, ep_payload=None):
        self.me_payload = me_payload or {
            "user": {
                "mediaProgress": [
                    {
                        "libraryItemId": "li_1",
                        "episodeId": None,
                        "duration": 1000.0,
                        "progress": 0.5,
                        "currentTime": 500.0,
                        "isFinished": False,
                        "lastUpdate": 1730000000000,
                    }
                ]
            }
        }
        self.item_payload = item_payload or {
            "item": {
                "mediaType": "book",
                "media": {
                    "metadata": {
                        "title": "T",
                        "authors": [{"name": "A"}],
                        "series": [{"name": "S"}],
                        "narrator": "N",
                        "publisher": "P",
                    }
                },
            }
        }
        self.ep_payload = ep_payload or {"episode": {"title": "Ep1"}}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, **_kwargs):
        class Resp:
            """Minimal response that returns the configured payload."""

            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        if url.endswith("/api/me"):
            return Resp(self.me_payload)
        if "/api/items/" in url:
            return Resp(self.item_payload)
        if "/api/podcasts/episodes/" in url:
            return Resp(self.ep_payload)
        return Resp({})


def test_fetch_playback_activity_book(monkeypatch):
    monkeypatch.setattr(abs_utils.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(abs_utils, "AUDIOBOOKSHELF_URL", "http://abs")
    # lastUpdate timestamp set above corresponds to 2024-10-26 UTC; accept any date
    # Recompute target date from timestamp for determinism
    date_str = "2024-10-26"
    result = asyncio.run(abs_utils.fetch_playback_activity(date_str))
    assert result and result[0]["title"] == "T"
    assert result[0]["author"] == "A"
    assert result[0]["series"] == "S"


def test_update_audio_metadata_writes(monkeypatch, tmp_path):
    monkeypatch.setattr(abs_utils.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(abs_utils, "AUDIOBOOKSHELF_URL", "http://abs")
    md = tmp_path / "2025-01-01.md"
    md.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")
    asyncio.run(abs_utils.update_audio_metadata("2024-10-26", md))
    out = md.parent / ".meta" / "2025-01-01.audio.json"
    assert out.exists()
