"""Prompt loading and generation helpers."""

import asyncio
import yaml
import random
from datetime import date

from activation_engine_utils import rank_prompts

import aiofiles

from config import PROMPTS_FILE, ENCODING

_prompts_cache: dict = {"data": None, "mtime": None}
_prompts_lock = asyncio.Lock()


async def load_prompts() -> list[dict]:
    """Load and cache journal prompts from ``PROMPTS_FILE``.

    The cache automatically invalidates when ``PROMPTS_FILE`` changes on disk.
    Returns an empty list if the file is missing or invalid.
    """
    try:
        mtime = PROMPTS_FILE.stat().st_mtime
    except FileNotFoundError:
        mtime = None

    if (
        _prompts_cache["data"] is None
        or _prompts_cache.get("mtime") != mtime
    ):
        async with _prompts_lock:
            if (
                _prompts_cache["data"] is None
                or _prompts_cache.get("mtime") != mtime
            ):
                try:
                    async with aiofiles.open(PROMPTS_FILE, "r", encoding=ENCODING) as fh:
                        prompts_text = await fh.read()
                    _prompts_cache["data"] = yaml.safe_load(prompts_text) or []
                    _prompts_cache["mtime"] = mtime
                except (FileNotFoundError, yaml.YAMLError):
                    _prompts_cache["data"] = []
                    _prompts_cache["mtime"] = mtime
    return _prompts_cache["data"]


def get_season(target_date: date) -> str:
    """Return the season name for the given date."""
    year = target_date.year
    spring_start = date(year, 3, 1)
    summer_start = date(year, 6, 1)
    autumn_start = date(year, 9, 1)
    winter_start = date(year, 12, 1)

    if spring_start <= target_date < summer_start:
        return "Spring"
    if summer_start <= target_date < autumn_start:
        return "Summer"
    if autumn_start <= target_date < winter_start:
        return "Autumn"
    return "Winter"


async def generate_prompt(tags: list[str] | None = None) -> dict:
    """Select and return a prompt for the current day.

    ``prompts.yaml`` now stores a list of prompt dictionaries with fields like
    ``id``, ``prompt`` and ``tags``.  This function chooses a prompt at random,
    optionally filtering by ``tags`` and using ActivationEngine to rank
    candidates when available.
    """
    today = date.today()
    weekday = today.strftime("%A")
    season = get_season(today)

    prompts = await load_prompts()
    if not isinstance(prompts, list) or not prompts:
        return {"category": None, "prompt": "Prompts file not found"}

    candidates = prompts
    if tags:
        tag_set = {t.lower() for t in tags}
        candidates = [
            p
            for p in prompts
            if any(tag.lower() in tag_set for tag in p.get("tags", []))
        ] or prompts

    if not candidates:
        return {"category": None, "prompt": "No prompts available"}

    if tags:
        ranked_strings = await rank_prompts([p.get("prompt", "") for p in candidates], tags)
        lookup = {p.get("prompt", ""): p for p in candidates}
        candidates = [lookup[s] for s in ranked_strings if s in lookup] or candidates

    chosen = random.choice(candidates)
    prompt_text = chosen.get("prompt", "")
    prompt_text = prompt_text.replace("{{weekday}}", weekday).replace("{{season}}", season)

    # Derive a category from the prompt id or tags
    category = None
    pid = chosen.get("id")
    if isinstance(pid, str):
        for sep in ("-", "_"):
            if sep in pid:
                category = pid.split(sep, 1)[0]
                break
    if not category:
        tags_list = chosen.get("tags")
        if tags_list:
            category = tags_list[0]

    result = {
        "prompt": prompt_text,
        "category": category.capitalize() if isinstance(category, str) else None,
        "id": pid,
        "tags": chosen.get("tags", []),
        "energy": chosen.get("energy"),
        "mood": chosen.get("mood"),
    }
    if "anchor" in chosen:
        result["anchor"] = chosen["anchor"]
    return result
