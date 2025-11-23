"""AudioBookShelf API integration utilities for audiobooks and podcasts."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from . import config

# Expose configuration values derived from config
AUDIOBOOKSHELF_URL = config.AUDIOBOOKSHELF_URL
AUDIOBOOKSHELF_API_TOKEN = config.AUDIOBOOKSHELF_API_TOKEN


def refresh_config() -> None:
    """Refresh module-level configuration aliases."""
    globals().update(
        AUDIOBOOKSHELF_URL=config.AUDIOBOOKSHELF_URL,
        AUDIOBOOKSHELF_API_TOKEN=config.AUDIOBOOKSHELF_API_TOKEN,
    )


logger = logging.getLogger("ej.audiobookshelf")


def _headers() -> Dict[str, str]:
    token = AUDIOBOOKSHELF_API_TOKEN or ""
    return {"Authorization": f"Bearer {token}"} if token else {}


def _is_date_match(ts_ms: int, target_date: str) -> bool:
    try:
        dt = datetime.fromtimestamp(ts_ms / 1000.0)
        return dt.date().isoformat() == target_date
    except Exception:  # defensive
        return False


def _join_dict_names(items: Any) -> Optional[str]:
    entries: List[str] = []
    if isinstance(items, list):
        for entry in items:
            if isinstance(entry, dict):
                value = entry.get("name")
                if isinstance(value, str):
                    entries.append(value)
    return ", ".join(entries) if entries else None


@dataclass(frozen=True)
class _AbsClientContext:
    client: httpx.AsyncClient
    url_base: str
    headers: Dict[str, str]


async def _fetch_library_item_metadata(
    context: _AbsClientContext,
    library_item_id: str,
    episode_id: Optional[str],
    duration: Optional[float],
) -> tuple[
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[float],
]:
    title = None
    author = None
    narrator = None
    publisher = None
    series = None
    duration_result = duration
    try:
        item_resp = await context.client.get(
            f"{context.url_base}/api/items/{library_item_id}",
            headers=context.headers,
            timeout=10,
        )
        item_resp.raise_for_status()
        item_data = item_resp.json() or {}
        media = (item_data.get("item") or item_data).get("media", {})
        media_type = (item_data.get("item") or item_data).get("mediaType")
        if media_type == "book":
            metadata = media.get("metadata", {})
            title = metadata.get("title")
            author = _join_dict_names(metadata.get("authors") or [])
            series = _join_dict_names(metadata.get("series") or [])
            narrator = metadata.get("narrator")
            publisher = metadata.get("publisher")
        elif media_type == "podcast":
            podcast_metadata = media.get("metadata", {})
            title = podcast_metadata.get("title")
            publisher = podcast_metadata.get("publisher")
            if episode_id:
                ep_title: Optional[str] = None
                ep_duration: Optional[float] = None
                try:
                    ep_resp = await context.client.get(
                        f"{context.url_base}/api/podcasts/episodes/{episode_id}",
                        headers=context.headers,
                        timeout=10,
                    )
                    ep_resp.raise_for_status()
                    ep_data = ep_resp.json() or {}
                    ep = ep_data.get("episode") or ep_data
                    ep_title = ep.get("title")
                    ep_duration = ep.get("audioFile") and ep.get("audioFile", {}).get(
                        "duration"
                    )
                except (httpx.HTTPError, ValueError, KeyError):
                    pass
                if ep_title:
                    series = title
                    title = ep_title
                if ep_duration and not duration_result:
                    duration_result = ep_duration
    except (httpx.HTTPError, ValueError, KeyError):
        pass
    return title, author, narrator, publisher, series, duration_result


async def _collect_media_progress_results(
    client: httpx.AsyncClient,
    url_base: str,
    headers: Dict[str, str],
    date_str: str,
    tz_offset: Optional[int],
) -> List[Dict[str, Any]]:
    resp = await client.get(f"{url_base}/api/me", headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json() or {}
    progress = data.get("user", {}).get("mediaProgress") or []
    logger.debug("ABS /api/me returned %d mediaProgress entries", len(progress))
    results: List[Dict[str, Any]] = []
    context = _AbsClientContext(client=client, url_base=url_base, headers=headers)
    for item in progress:
        last = item.get("progressLastUpdate") or item.get("lastUpdate")
        if not isinstance(last, int):
            continue
        adj = last + (tz_offset * 60_000) if tz_offset is not None else last
        if not _is_date_match(adj, date_str):
            continue
        duration = item.get("duration")
        progress_pct = item.get("progress")
        current_time = item.get("currentTime")
        finished = item.get("isFinished")
        li_id = item.get("libraryItemId")
        ep_id = item.get("episodeId")
        title = None
        author = None
        narrator = None
        publisher = None
        series = None
        metadata_duration = duration
        if li_id:
            (
                title,
                author,
                narrator,
                publisher,
                series,
                metadata_duration,
            ) = await _fetch_library_item_metadata(
                context,
                li_id,
                ep_id,
                duration,
            )
        results.append(
            {
                "abs_library_item_id": li_id,
                "abs_episode_id": ep_id,
                "title": title,
                "author": author,
                "narrator": narrator,
                "publisher": publisher,
                "series": series,
                "duration": metadata_duration,
                "progress": progress_pct,
                "current_time": current_time,
                "is_finished": finished,
                "last_update": last,
            }
        )
    return results


async def _collect_personalized_library_entries(
    client: httpx.AsyncClient,
    url_base: str,
    headers: Dict[str, str],
    date_str: str,
    tz_offset: Optional[int],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    libs_resp = await client.get(
        f"{url_base}/api/libraries", headers=headers, timeout=10
    )
    libs_resp.raise_for_status()
    libs = libs_resp.json() or []
    lib_list = libs if isinstance(libs, list) else libs.get("libraries") or []
    for lib in lib_list:
        lib_id = lib.get("id") or lib.get("libraryId") or lib.get("_id")
        if not lib_id:
            continue
        try:
            p_resp = await client.get(
                f"{url_base}/api/libraries/{lib_id}/personalized",
                headers=headers,
                timeout=10,
            )
            p_resp.raise_for_status()
            pdata = p_resp.json() or {}
            categories = (
                pdata if isinstance(pdata, list) else pdata.get("categories") or []
            )
            for cat in categories:
                for entity in cat.get("entities", []) or []:
                    last_ms = entity.get("progressLastUpdate") or entity.get(
                        "lastUpdate"
                    )
                    if not isinstance(last_ms, int):
                        continue
                    adj_ms = (
                        last_ms + (tz_offset * 60_000)
                        if tz_offset is not None
                        else last_ms
                    )
                    if not _is_date_match(adj_ms, date_str):
                        continue
                    md = entity.get("media", {}).get("metadata", {})
                    title = md.get("title")
                    author = _join_dict_names(md.get("authors") or [])
                    narrator = md.get("narrator")
                    publisher = md.get("publisher")
                    series = _join_dict_names(md.get("series") or [])
                    results.append(
                        {
                            "abs_library_item_id": entity.get("id"),
                            "abs_episode_id": None,
                            "title": title,
                            "author": author,
                            "narrator": narrator,
                            "publisher": publisher,
                            "series": series,
                            "duration": entity.get("duration"),
                            "progress": entity.get("progress"),
                            "current_time": entity.get("currentTime"),
                            "is_finished": entity.get("isFinished"),
                            "last_update": last_ms,
                        }
                    )
        except (httpx.HTTPError, ValueError, KeyError):
            pass
    return results


async def fetch_playback_activity(
    date_str: str, tz_offset: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Return audiobook/podcast playback activity for the given date.

    Pulls recent media progress for the authenticated user and filters entries
    to those updated on ``date_str``. Includes ABS-specific identifiers.
    """
    if not AUDIOBOOKSHELF_URL:
        logger.info("AudioBookShelf integration disabled; skipping fetch")
        return []

    headers = _headers()
    logger.info("Fetching AudioBookShelf playback for %s", date_str)
    url_base = AUDIOBOOKSHELF_URL.rstrip("/")
    try:
        async with httpx.AsyncClient() as client:
            results = await _collect_media_progress_results(
                client, url_base, headers, date_str, tz_offset
            )
            if results:
                logger.info("Returning %d AudioBookShelf records", len(results))
                return results

            results = await _collect_personalized_library_entries(
                client, url_base, headers, date_str, tz_offset
            )
            logger.info("Returning %d AudioBookShelf records", len(results))
            return results
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Error fetching AudioBookShelf activity: %s", exc)
        return []


async def debug_playback(
    date_str: str, tz_offset: Optional[int] = None
) -> Dict[str, Any]:
    if not AUDIOBOOKSHELF_URL:
        return {"error": "AudioBookShelf integration disabled"}
    url_base = AUDIOBOOKSHELF_URL.rstrip("/")
    headers = _headers()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{url_base}/api/me", headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json() or {}
            progress = data.get("user", {}).get("mediaProgress") or []
            items: List[Dict[str, Any]] = []
            for item in progress:
                last = item.get("progressLastUpdate") or item.get("lastUpdate")
                if not isinstance(last, int):
                    continue
                adj = last + (tz_offset * 60_000) if tz_offset is not None else last
                utc_date = _is_date_match(last, date_str)
                local_date = _is_date_match(adj, date_str)
                li_id = item.get("libraryItemId")
                ep_id = item.get("episodeId")
                title = None
                series = None
                try:
                    if li_id:
                        iresp = await client.get(
                            f"{url_base}/api/items/{li_id}", headers=headers, timeout=10
                        )
                        iresp.raise_for_status()
                        idata = iresp.json() or {}
                        media = (idata.get("item") or idata).get("media", {})
                        mtype = (idata.get("item") or idata).get("mediaType")
                        if mtype == "book":
                            md = media.get("metadata", {})
                            title = md.get("title")
                        elif mtype == "podcast":
                            md = media.get("metadata", {})
                            series = md.get("title")
                            if ep_id:
                                eresp = await client.get(
                                    f"{url_base}/api/podcasts/episodes/{ep_id}",
                                    headers=headers,
                                    timeout=10,
                                )
                                eresp.raise_for_status()
                                edata = eresp.json() or {}
                                ep = edata.get("episode") or edata
                                title = ep.get("title")
                except (httpx.HTTPError, ValueError, KeyError) as exc:
                    logger.debug("Failed to load ABS metadata for %s: %s", li_id, exc)
                items.append(
                    {
                        "libraryItemId": li_id,
                        "episodeId": ep_id,
                        "title": title,
                        "series": series,
                        "duration": item.get("duration"),
                        "progress": item.get("progress"),
                        "currentTime": item.get("currentTime"),
                        "isFinished": item.get("isFinished"),
                        "lastUpdate": last,
                        "matches_utc": utc_date,
                        "matches_local": local_date,
                    }
                )
            return {"count": len(items), "items": items}
    except (httpx.HTTPError, ValueError) as exc:
        return {"error": str(exc)}


async def update_audio_metadata(
    date_str: str, journal_path: Path, tz_offset: Optional[int] = None
) -> None:
    """Fetch audio playback for the date and save to ``.audio.json``."""
    logger.info("Updating AudioBookShelf metadata for %s", journal_path)
    records = await fetch_playback_activity(date_str, tz_offset=tz_offset)
    if not records:
        logger.info("No AudioBookShelf data for %s", date_str)
        return

    meta_dir = journal_path.parent / ".meta"
    try:
        meta_dir.mkdir(parents=True, exist_ok=True)
        out_path = meta_dir / f"{journal_path.stem}.audio.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        logger.info("Wrote %d audio records to %s", len(records), out_path)
    except OSError as exc:
        logger.error("Failed to write audio metadata file: %s", exc)
