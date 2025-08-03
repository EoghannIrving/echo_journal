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

async def rank_prompts(prompts: List[str], tags: List[str]) -> List[str]:
    """Return prompts sorted by relevance via ActivationEngine."""
    if not ACTIVATION_ENGINE_URL:
        return prompts
    url = f"{ACTIVATION_ENGINE_URL.rstrip('/')}/rank-tasks"
    payload = {"tasks": [
        {"name": p, "project": "prompt"} for p in prompts
    ], "user_state": {"mood": None, "energy": 3, "context": {}}}
    if tags:
        payload["user_state"]["mood"] = tags[0]
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates")
            if isinstance(candidates, list):
                return [
                    c.get("task", c)
                    for c in candidates
                    if isinstance(c, (dict, str))
                ]
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("ActivationEngine rank-tasks failed: %s", exc)
    return prompts
