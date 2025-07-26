"""Utilities for interacting with the Immich API."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timedelta

import aiofiles
import httpx

from config import IMMICH_URL, IMMICH_API_KEY, ENCODING
import os

# Allow widening the search range so photos close to midnight in other
# timezones are included. The default of 12 hours covers all time zones.
IMMICH_TIME_BUFFER = int(os.getenv("IMMICH_TIME_BUFFER", "12"))

logger = logging.getLogger("ej.immich")

async def fetch_assets_for_date(
    date_str: str, media_type: str = "IMAGE"
) -> List[Dict[str, Any]]:
    """Return a list of assets for the given date from the Immich API."""
    if not IMMICH_URL:
        logger.info("Immich integration disabled; skipping fetch")
        return []

    # Expand the search range on either side of ``date_str`` to compensate
    # for timezone differences between where photos were taken and UTC.
    date = datetime.strptime(date_str, "%Y-%m-%d")
    start = date - timedelta(hours=IMMICH_TIME_BUFFER)
    end = date + timedelta(days=1, hours=IMMICH_TIME_BUFFER) - timedelta(seconds=1)

    payload = {
        "createdAfter": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "createdBefore": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": media_type,
    }

    headers = {"x-api-key": IMMICH_API_KEY} if IMMICH_API_KEY else {}

    logger.info("Fetching assets for %s from %s/api/search/metadata", date_str, IMMICH_URL)

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
            logger.debug("Immich raw response: %s", data)

            if isinstance(data, dict) and "assets" in data:
                assets = data["assets"].get("items", [])
                logger.info("Received %d assets", len(assets))
                return assets

    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Error fetching assets from Immich: %s", exc)
        return []

    return []

async def update_photo_metadata(date_str: str, journal_path: Path) -> None:
    """Fetch photo assets from Immich and save metadata alongside journal entry."""
    logger.info("Updating photo metadata for %s", journal_path)

    try:
        assets = await fetch_assets_for_date(date_str, media_type="IMAGE")
    except Exception as e:
        logger.error("Failed to fetch assets for %s: %s", date_str, e)
        return

    if not assets:
        logger.info("No photo assets found for %s", date_str)
        return

    logger.info("Found %d photo assets for %s", len(assets), date_str)

    photo_metadata = []
    for asset in assets:
        asset_id = asset.get("id")
        if not asset_id:
            continue
        photo_metadata.append({
            "url": f"{IMMICH_URL}/assets/{asset_id}",
            "thumb": f"{IMMICH_URL}/assets/{asset_id}/thumbnail?size=medium",
            "caption": asset.get("originalFileName", "")
        })

    photo_path = journal_path.with_suffix(".photos.json")
    try:
        with open(photo_path, "w", encoding="utf-8") as f:
            json.dump(photo_metadata, f, indent=2)
        logger.info("Wrote %d photo records to %s", len(photo_metadata), photo_path)
    except Exception as e:
        logger.error("Failed to write photo metadata file: %s", e)
