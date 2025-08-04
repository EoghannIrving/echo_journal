"""Utility functions for generating prompts via an AI API."""

from typing import Optional

import httpx

from . import config

OPENAI_URL = "https://api.openai.com/v1/completions"


async def fetch_ai_prompt() -> Optional[str]:
    """Return a generated prompt from an AI service if available.

    Uses ``config.OPENAI_API_KEY`` which may be provided via ``settings.yaml`` or
    environment variables. Returns ``None`` if the key is missing or the request
    fails for any reason.
    """

    api_key = config.OPENAI_API_KEY
    if not api_key:
        return None

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "gpt-3.5-turbo-instruct",
        "prompt": "Give me a short journaling prompt.",
        "max_tokens": 60,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(OPENAI_URL, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                text = choices[0].get("text")
                if isinstance(text, str):
                    return text.strip()
    except (httpx.HTTPError, ValueError, KeyError):
        return None

    return None
