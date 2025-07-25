"""Utilities for interacting with the Immich API."""

import json
from pathlib import Path
from typing import List, Dict, Any

import httpx
import aiofiles

from config import IMMICH_URL, IMMICH_API_KEY, ENCODING


async def fetch_assets_for_date(
    date_str: str, media_type: str = "IMAGE"
) -> List[Dict[str, Any]]:
    """Return a list of assets for the given date from the Immich API."""
    if not IMMICH_URL:
        return []

    payload = {
        "createdAt": {
            "min": f"{date_str}T00:00:00Z",
            "max": f"{date_str}T23:59:59Z",
        },
        "type": media_type,
    }
    headers = {"x-api-key": IMMICH_API_KEY} if IMMICH_API_KEY else {}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{IMMICH_URL}/asset/search",
                json=payload,
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and isinstance(data.get("assets"), list):
                return data["assets"]
    except (httpx.HTTPError, ValueError):
        return []
    return []


async def update_photo_metadata(entry_path: Path) -> None:
    """Fetch photo metadata for the entry date and save to a companion JSON file."""
    date_str = entry_path.stem
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
        return

    json_path = entry_path.with_suffix(".photos.json")
    async with aiofiles.open(json_path, "w", encoding=ENCODING) as fh:
        await fh.write(json.dumps(photos))
