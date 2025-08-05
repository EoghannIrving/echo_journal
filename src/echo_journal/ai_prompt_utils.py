"""Utility functions for generating prompts via an AI API."""

from typing import Optional, Dict, Any

import httpx
import yaml
import logging

from . import config

CHAT_URL = "https://api.openai.com/v1/chat/completions"

AI_PROMPT_TEMPLATE = (
    "You are a journaling assistant for Echo Journal. Your job is to generate"
    " journaling prompts that match an anchor level of {anchor} and with 1-2"
    " thematic strategies (tags). All prompts have the goal of helping the writer connect better with the day they are writing about.\n\n"
    "Anchor Levels\n"
    "micro: Can be answered in one word, emoji, or phrase. Used when energy is very low.\n"
    "soft: Gentle observational or sensory prompts. Easy to start, low emotional load.\n"
    "moderate: Encourages reflection or meaning-making, but not emotionally intense.\n"
    "strong: Deep, personal, or narrative-based prompts. Requires emotional readiness.\n\n"
    "Strategy Tags\n"
    "Each prompt should align with 1–2 of these:\n\n"
    "senses: describe sensory detail (touch, sound, smell, color)\n"
    "context: what led to something, location, environment\n"
    "scene: describe a moment visually or like a painting\n"
    "contrast: explore difference or opposites\n"
    "list: list things with elaboration (e.g. \"3 things and why\")\n"
    "mood: explore feelings and what caused them\n"
    "hypothetical: imagined or alternate scenarios\n"
    "deep: reflection on meaning, significance, values\n"
    "temporal: linked to time — morning, today, now, earlier\n"
    "narrative: tells a story, sequence of events, interaction\n\n"
    "Format\n"
    "Return the result in strict YAML:\n\n"
    "- id: <tag>-<3-digit number>\n"
    "  prompt: \"<journal prompt>\"\n"
    "  tags:\n"
    "    - tag1\n"
    "    - tag2\n"
    "  anchor: <anchor>"
)

logger = logging.getLogger("ej.ai_prompt")


async def fetch_ai_prompt(anchor: str | None) -> Optional[Dict[str, Any]]:
    """Return a generated prompt as a dict from an AI service.

    Uses ``config.OPENAI_API_KEY`` which may be provided via ``settings.yaml`` or
    environment variables. Returns ``None`` if the key is missing, ``anchor`` is
    ``None`` or the request fails for any reason.
    """

    logger.debug("Fetching AI prompt with anchor=%s", anchor)
    api_key = config.OPENAI_API_KEY
    if not api_key:
        logger.warning("OPENAI_API_KEY missing; cannot fetch AI prompt")
        return None
    if not anchor:
        logger.warning("Anchor missing; cannot fetch AI prompt")
        return None

    headers = {"Authorization": f"Bearer {api_key}"}
    prompt_text = AI_PROMPT_TEMPLATE.format(anchor=anchor)
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": 300,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(CHAT_URL, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices")
            if not isinstance(choices, list) or not choices:
                logger.warning("AI response missing choices: %s", data)
                return None
            message = choices[0].get("message", {})
            content = message.get("content")

            if isinstance(content, list):
                text_parts = [
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                content = "".join(text_parts)

            if not isinstance(content, str) or not content.strip():
                logger.warning("AI response had empty content: %s", content)
                return None

            content = content.strip()
            if content.startswith("```"):
                lines = content.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()

            logger.debug("AI returned content: %s", content)

            parsed = yaml.safe_load(content)
            if isinstance(parsed, list) and parsed:
                first = parsed[0]
                if isinstance(first, dict):
                    return first
            logger.warning("AI response not in expected format: %s", content)
    except (httpx.HTTPError, ValueError, KeyError, yaml.YAMLError) as exc:
        logger.error("AI prompt fetch failed: %s", exc)
        return None

    return None
