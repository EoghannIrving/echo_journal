"""Utility functions for interacting with the Wordnik API."""

# pylint: disable=duplicate-code

from typing import Optional, Tuple

import httpx

from . import config

# Expose API key for tests while deriving from configuration
WORDNIK_API_KEY = config.WORDNIK_API_KEY
WORDNIK_URL = "https://api.wordnik.com/v4/words.json/wordOfTheDay"


def refresh_config() -> None:
    """Refresh module-level configuration aliases."""
    global WORDNIK_API_KEY
    WORDNIK_API_KEY = config.WORDNIK_API_KEY


async def fetch_word_of_day() -> Optional[Tuple[str, str]]:
    """Return today's Wordnik word of the day and definition if available."""

    api_key = WORDNIK_API_KEY
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                WORDNIK_URL, params={"api_key": api_key}, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            word = data.get("word")
            definition = ""
            defs = data.get("definitions")
            if isinstance(defs, list) and defs:
                first = defs[0]
                if isinstance(first, dict):
                    text = first.get("text")
                    if isinstance(text, str):
                        definition = text
            if isinstance(word, str):
                return word, definition
    except (httpx.HTTPError, ValueError):
        return None
    return None
