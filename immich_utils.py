"""Utilities for interacting with the Immich API."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import aiofiles
import httpx

from config import IMMICH_URL, IMMICH_API_KEY, ENCODING

logger = logging.getLogger("ej.immich")


async def fetch_assets_for_date(
    date_str: str, media_type: str = "IMAGE"
) -> List[Dict[str, Any]]:
    """Return a list of assets for the given date from the Immich API."""
    if not IMMICH_URL:
        logger.info("Immich integration disabled; skipping fetch")
        return []

    payload = {
        "createdAt": {
            "min": f"{date_str}T00:00:00Z",
            "max": f"{date_str}T23:59:59Z",
        },
        "type": media_type,
    }
    headers = {"x-api-key": IMMICH_API_KEY} if IMMICH_API_KEY else {}
    logger.info("Fetching assets for %s from %s/asset/search", date_str, IMMICH_URL)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{IMMICH_URL}/search/metadata",
                headers=headers,
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                logger.info("Received %d assets", len(data))
                return data
            if isinstance(data, dict) and isinstance(data.get("assets"), list):
                logger.info("Received %d assets", len(data["assets"]))
                return data["assets"]
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Error fetching assets from Immich: %s", exc)
        return []
    return []


async def update_photo_metadata(entry_path: Path) -> None:
    """Fetch photo metadata for the entry date and save to a companion JSON file."""
    date_str = entry_path.stem
    logger.info("Updating photo metadata for %s", entry_path)
    assets = await fetch_assets_for_date(date_str)
    photos = []
    for asset in assets:
        if asset.get("type") != "IMAGE":
            continue
        photos.append(
            {
                "url": asset.get("url"),
                "thumb": asset.get("thumb"),
                "caption": asset.get("caption", ""),
            }
        )
    if not photos:
        logger.info("No photo assets found for %s", date_str)
        return

    json_path = entry_path.with_suffix(".photos.json")
    async with aiofiles.open(json_path, "w", encoding=ENCODING) as fh:
        await fh.write(json.dumps(photos))
    logger.info("Wrote %d photos to %s", len(photos), json_path)
