"""Helpers for talking to the external Activation Engine service."""

import logging
from typing import List
import httpx

from config import ACTIVATION_ENGINE_URL

logger = logging.getLogger("ej.activation")

async def fetch_tags(mood: str, energy: str, context: str) -> List[str]:
    """Return tags from ActivationEngine based on the given state."""
    if not ACTIVATION_ENGINE_URL:
        return []
    url = f"{ACTIVATION_ENGINE_URL.rstrip('/')}/get-tags"
    payload = {"mood": mood, "energy": energy, "context": {"last_activity": context}}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            tags = data.get("tags")
            if isinstance(tags, list):
                return [str(t) for t in tags]
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("ActivationEngine get-tags failed: %s", exc)
    return []
