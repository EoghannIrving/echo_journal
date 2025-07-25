"""Utility functions for interacting with the Wordnik API."""

import os
from typing import Optional
import httpx

WORDNIK_URL = "https://api.wordnik.com/v4/words.json/wordOfTheDay"

async def fetch_word_of_day() -> Optional[str]:
    """Return today's Wordnik word of the day if available."""
    api_key = os.getenv("WORDNIK_API_KEY")
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(WORDNIK_URL, params={"api_key": api_key}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            word = data.get("word")
            if isinstance(word, str):
                return word
    except (httpx.HTTPError, ValueError):
        return None
    return None
