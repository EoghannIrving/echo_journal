"""Helpers for fetching date facts from numbersapi.com."""

from datetime import date
from typing import Optional

import httpx


async def fetch_date_fact(day: date) -> Optional[str]:
    """Return a fact string for the given date.

    Uses numbersapi.com to fetch a trivia fact about the supplied date.
    Returns ``None`` if the request fails or the response is malformed.
    """
    url = f"https://numbersapi.com/{day.month}/{day.day}/date?json"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            text = data.get("text")
            if text:
                return text
    except (httpx.HTTPError, ValueError):
        return None
    return None
