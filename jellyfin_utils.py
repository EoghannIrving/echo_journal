"""Jellyfin API integration utilities."""

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, AsyncIterator
import os

import httpx

from config import (
    JELLYFIN_URL,
    JELLYFIN_API_KEY,
    JELLYFIN_USER_ID,
    JELLYFIN_PLAY_THRESHOLD,
)

logger = logging.getLogger("ej.jellyfin")

# Number of items to request per page when fetching play history.
JELLYFIN_PAGE_SIZE = int(os.getenv("JELLYFIN_PAGE_SIZE", "200"))


async def _iter_items(
    date_str: str, headers: Dict[str, str], url: str, base_params: Dict[str, str]
) -> AsyncIterator[Dict[str, Any]]:
    """Yield Jellyfin play history items until ``date_str`` is passed."""
    start_index = 0
    async with httpx.AsyncClient() as client:
        while True:
            params = {
                **base_params,
                "Limit": str(JELLYFIN_PAGE_SIZE),
                "StartIndex": str(start_index),
            }
            logger.debug("Requesting %s with params %s", url, params)
            resp = await client.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            page_items = resp.json().get("Items", [])
            logger.info(
                "Received %d items from Jellyfin (start=%d)",
                len(page_items),
                start_index,
            )
            if not page_items:
                break
            for item in page_items:
                yield item
            last_played = page_items[-1].get("DatePlayed") or page_items[-1].get(
                "UserData", {}
            ).get("LastPlayedDate")
            start_index += JELLYFIN_PAGE_SIZE
            if not last_played:
                logger.debug("No last played date in page starting %d", start_index)
                continue
            try:
                last_date = (
                    datetime.fromisoformat(last_played.replace("Z", "+00:00"))
                    .date()
                    .isoformat()
                )
            except ValueError:
                logger.debug("Could not parse last played date: %s", last_played)
                continue
            if last_date < date_str or len(page_items) < JELLYFIN_PAGE_SIZE:
                logger.debug(
                    "Stopping iteration: last_date=%s, page_len=%d",
                    last_date,
                    len(page_items),
                )
                break


async def fetch_top_songs(date_str: str) -> List[Dict[str, Any]]:
    """Return today's top songs from Jellyfin for the configured user."""
    if not JELLYFIN_URL or not JELLYFIN_USER_ID:
        logger.info("Jellyfin integration disabled; skipping fetch")
        return []

    headers = {"X-Emby-Token": JELLYFIN_API_KEY} if JELLYFIN_API_KEY else {}
    url = f"{JELLYFIN_URL}/Users/{JELLYFIN_USER_ID}/Items"
    logger.info("Fetching Jellyfin plays for %s", date_str)
    base_params = {
        "Filters": "IsPlayed",
        "IncludeItemTypes": "Audio",
        "Fields": "DatePlayed,ArtistItems",
        "SortBy": "DatePlayed",
        "SortOrder": "Descending",
        "Recursive": "true",
    }

    counts: Counter[tuple[str, str]] = Counter()
    last_played: Dict[tuple[str, str], datetime] = {}

    try:
        async for item in _iter_items(date_str, headers, url, base_params):
            played = item.get("DatePlayed") or item.get("UserData", {}).get(
                "LastPlayedDate"
            )
            if not played:
                logger.debug("Skipping item with no play date: %s", item.get("Name"))
                continue
            try:
                play_dt = datetime.fromisoformat(played.replace("Z", "+00:00"))
                if play_dt.date().isoformat() != date_str:
                    logger.debug(
                        "Skipping play dated %s (target %s)",
                        play_dt.date().isoformat(),
                        date_str,
                    )
                    continue
            except ValueError:
                logger.debug("Could not parse play date %s", played)
                continue
            track = item.get("Name", "Unknown Title")
            artist = (
                " / ".join(
                    a.get("Name", "Unknown Artist")
                    for a in item.get("ArtistItems", [])
                )
                or "Unknown Artist"
            )
            played_pct = item.get("UserData", {}).get("PlayedPercentage")
            if played_pct is not None and played_pct < JELLYFIN_PLAY_THRESHOLD:
                logger.debug(
                    "Skipping %s - %s below threshold: %.1f%%",
                    track,
                    artist,
                    played_pct,
                )
                continue
            key = (track, artist)
            counts[key] += 1
            if key not in last_played or play_dt > last_played[key]:
                last_played[key] = play_dt
            logger.debug("Counted play for %s - %s", track, artist)
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Error fetching Jellyfin items: %s", exc)
        return []
    logger.debug("Raw play counts: %s", counts)
    sorted_counts = sorted(
        counts.items(),
        key=lambda item: (
            -item[1],
            -last_played[item[0]].timestamp(),
        ),
    )[:20]
    logger.info("Returning %d track records", len(sorted_counts))
    return [
        {"track": track, "artist": artist, "plays": cnt}
        for (track, artist), cnt in sorted_counts
    ]


async def update_song_metadata(date_str: str, journal_path: Path) -> None:
    """Fetch top songs for the date and store them next to the journal entry."""
    logger.info("Updating song metadata for %s", journal_path)
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

async def fetch_daily_media(date_str: str) -> List[Dict[str, Any]]:
    """Return watched movies and episodes for the given date."""
    if not JELLYFIN_URL or not JELLYFIN_USER_ID:
        logger.info("Jellyfin integration disabled; skipping fetch")
        return []

    headers = {"X-Emby-Token": JELLYFIN_API_KEY} if JELLYFIN_API_KEY else {}
    url = f"{JELLYFIN_URL}/Users/{JELLYFIN_USER_ID}/Items"
    logger.info("Fetching Jellyfin media for %s", date_str)
    base_params = {
        "Filters": "IsPlayed",
        "IncludeItemTypes": "Episode,Movie",
        "Fields": "DatePlayed,SeriesName",
        "SortBy": "DatePlayed",
        "SortOrder": "Descending",
        "Recursive": "true",
    }

    records: List[Dict[str, str]] = []
    try:
        async for item in _iter_items(date_str, headers, url, base_params):
            played = item.get("DatePlayed") or item.get("UserData", {}).get(
                "LastPlayedDate"
            )
            if not played:
                continue
            try:
                play_dt = datetime.fromisoformat(played.replace("Z", "+00:00"))
                if play_dt.date().isoformat() != date_str:
                    continue
            except ValueError:
                continue
            played_pct = item.get("UserData", {}).get("PlayedPercentage")
            if played_pct is not None and played_pct < JELLYFIN_PLAY_THRESHOLD:
                continue
            title = item.get("Name", "Unknown")
            series = item.get("SeriesName") or ""
            records.append({"title": title, "series": series})
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Error fetching Jellyfin items: %s", exc)
        return []

    logger.info("Returning %d media records", len(records))
    return records


async def update_media_metadata(date_str: str, journal_path: Path) -> None:
    """Fetch movies/TV watched for the date and save to ``.media.json``."""
    logger.info("Updating media metadata for %s", journal_path)
    media = await fetch_daily_media(date_str)
    if not media:
        logger.info("No media data for %s", date_str)
        return

    media_path = journal_path.with_suffix(".media.json")
    try:
        with open(media_path, "w", encoding="utf-8") as f:
            json.dump(media, f, indent=2)
        logger.info("Wrote %d media records to %s", len(media), media_path)
    except OSError as exc:
        logger.error("Failed to write media metadata file: %s", exc)

