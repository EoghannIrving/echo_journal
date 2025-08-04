"""Utility functions for generating prompts via an AI API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import httpx

OPENAI_URL = "https://api.openai.com/v1/completions"

# Load the prompt classification guidelines once so the request to the model can
# include the relevant context.  The file lives at the project root.
CLASSIFICATION_GUIDE = (
    Path(__file__).resolve().parents[2] / "PROMPT_CLASSIFICATION.md"
).read_text(encoding="utf-8")


async def fetch_ai_prompt() -> Optional[dict[str, object]]:
    """Return a generated prompt with classification metadata.

    The function contacts an external AI service using ``OPENAI_API_KEY``.  A
    ``None`` return indicates either the key was missing or the request/response
    was invalid.  On success a dictionary with ``prompt``, ``anchor`` and
    ``tags`` keys is returned.
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    headers = {"Authorization": f"Bearer {api_key}"}
    # Craft the message so the model knows about the classification system and
    # can respond with structured data describing the generated prompt.
    instruction = (
        "Using the following classification system, create one journaling prompt "
        "and label it. Respond ONLY with JSON containing the keys 'prompt', "
        "'anchor', and 'tags'.\n"
        f"{CLASSIFICATION_GUIDE}"
    )
    payload = {
        "model": "gpt-3.5-turbo-instruct",
        "prompt": instruction,
        "max_tokens": 120,
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
                    try:
                        result = json.loads(text)
                        prompt = result.get("prompt")
                        anchor = result.get("anchor")
                        tags = result.get("tags")
                        if isinstance(prompt, str) and isinstance(anchor, str) and isinstance(tags, list):
                            return {"prompt": prompt.strip(), "anchor": anchor, "tags": tags}
                    except json.JSONDecodeError:
                        return None
    except (httpx.HTTPError, ValueError, KeyError):
        return None

    return None
