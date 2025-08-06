"""Utilities for interacting with the Immich API."""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import httpx

from . import config

# Expose configuration values for tests while deriving from the config module.
IMMICH_URL = config.IMMICH_URL
IMMICH_API_KEY = config.IMMICH_API_KEY
IMMICH_TIME_BUFFER = config.IMMICH_TIME_BUFFER

# ``config.IMMICH_TIME_BUFFER`` ensures empty environment values fall back to
# the default defined in the configuration module.


def refresh_config() -> None:
    """Refresh module-level configuration aliases."""
    globals().update(
        IMMICH_URL=config.IMMICH_URL,
        IMMICH_API_KEY=config.IMMICH_API_KEY,
        IMMICH_TIME_BUFFER=config.IMMICH_TIME_BUFFER,
    )

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
    # ``date_str`` is interpreted as midnight in the server's local timezone
    # and converted to UTC before being sent to the Immich API.  The previous
    # implementation treated local times as UTC directly which could shift the
    # query window by the server's timezone offset.
    local_tz = datetime.now().astimezone().tzinfo
    date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=local_tz)
    start = date - timedelta(hours=IMMICH_TIME_BUFFER)
    end = date + timedelta(days=1, hours=IMMICH_TIME_BUFFER) - timedelta(seconds=1)

    payload = {
        "takenAfter": start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "takeBefore": end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": media_type,
    }

    headers = {"x-api-key": IMMICH_API_KEY} if IMMICH_API_KEY else {}

    logger.info(
        "Fetching assets for %s from %s/api/search/metadata", date_str, IMMICH_URL
    )

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

    assets = await fetch_assets_for_date(date_str, media_type="IMAGE")

    if not assets:
        logger.info("No photo assets found for %s", date_str)
        return

    logger.info("Found %d photo assets for %s", len(assets), date_str)

    photo_metadata = []
    for asset in assets:
        created = asset.get("fileCreatedAt")
        if not created:
            logger.debug("Skipping asset without fileCreatedAt: %s", asset)
            continue
        try:
            created_date = (
                datetime.fromisoformat(created.replace("Z", "+00:00"))
                .date()
                .isoformat()
            )
            if created_date != date_str:
                logger.debug(
                    "Skipping asset %s with date %s (target %s)",
                    asset.get("id"),
                    created_date,
                    date_str,
                )
                continue
        except ValueError:
            logger.debug("Could not parse fileCreatedAt: %s", created)
            continue

        asset_id = asset.get("id")
        if not asset_id:
            continue
        photo_metadata.append(
            {
                "url": f"/api/asset/{asset_id}",
                "thumb": f"/api/thumbnail/{asset_id}?size=thumbnail",
                "caption": asset.get("originalFileName", ""),
            }
        )

    meta_dir = journal_path.parent / ".meta"
    try:
        meta_dir.mkdir(parents=True, exist_ok=True)
        photo_path = meta_dir / f"{journal_path.stem}.photos.json"
        with open(photo_path, "w", encoding="utf-8") as f:
            json.dump(photo_metadata, f, indent=2)
        logger.info("Wrote %d photo records to %s", len(photo_metadata), photo_path)
    except OSError as exc:
        logger.error("Failed to write photo metadata file: %s", exc)
