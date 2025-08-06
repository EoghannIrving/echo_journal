"""Helpers for fetching random facts from uselessfacts.jsph.pl."""

from datetime import date
from typing import Optional

import httpx


async def fetch_date_fact(_: date) -> Optional[str]:
    """Return a random useless fact.

    Fetches a random fact from ``uselessfacts.jsph.pl``. The ``date`` argument is
    ignored. Returns ``None`` if the request fails or the response is malformed.
    """
    url = "https://uselessfacts.jsph.pl/api/v2/facts/random"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params={"language": "en"}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            text = data.get("text")
            if text:
                return text
    except (httpx.HTTPError, ValueError):
        return None
    return None
