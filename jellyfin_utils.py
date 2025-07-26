"""Jellyfin API integration utilities."""

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import httpx

from config import JELLYFIN_URL, JELLYFIN_API_KEY, JELLYFIN_USER_ID

logger = logging.getLogger("ej.jellyfin")


async def fetch_top_songs(date_str: str) -> List[Dict[str, Any]]:
    """Return today's top songs from Jellyfin for the configured user."""
    if not JELLYFIN_URL or not JELLYFIN_USER_ID:
        logger.info("Jellyfin integration disabled; skipping fetch")
        return []

    headers = {"X-Emby-Token": JELLYFIN_API_KEY} if JELLYFIN_API_KEY else {}
    url = f"{JELLYFIN_URL}/Users/{JELLYFIN_USER_ID}/Items"
    params = {
        "Filters": "IsPlayed",
        "IncludeItemTypes": "Audio",
        "Fields": "DatePlayed,ArtistItems",
        "SortBy": "DatePlayed",
        "SortOrder": "Descending",
        "Recursive": "true",
        "Limit": "1000",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("Items", [])
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Error fetching Jellyfin items: %s", exc)
        return []

    todays_tracks: List[tuple[str, str]] = []
    for item in items:
        played = item.get("DatePlayed")
        if not played:
            continue
        try:
            if (
                datetime.fromisoformat(played.replace("Z", "+00:00")).date().isoformat()
                != date_str
            ):
                continue
        except ValueError:
            continue
        name = item.get("Name", "Unknown Title")
        artist = (
            " / ".join(
                a.get("Name", "Unknown Artist") for a in item.get("ArtistItems", [])
            )
            or "Unknown Artist"
        )
        todays_tracks.append((name, artist))

    counts = Counter(todays_tracks).most_common(5)
    return [
        {"track": track, "artist": artist, "plays": cnt}
        for (track, artist), cnt in counts
    ]


async def update_song_metadata(date_str: str, journal_path: Path) -> None:
    """Fetch top songs for the date and store them next to the journal entry."""
    songs = await fetch_top_songs(date_str)
    if not songs:
        logger.info("No song data for %s", date_str)
        return

    song_path = journal_path.with_suffix(".songs.json")
    try:
        with open(song_path, "w", encoding="utf-8") as f:
            json.dump(songs, f, indent=2)
        logger.info("Wrote %d song records to %s", len(songs), song_path)
    except OSError as exc:
        logger.error("Failed to write song metadata file: %s", exc)
