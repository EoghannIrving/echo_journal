"""Prompt loading and generation helpers."""

import asyncio
import json
import random
from datetime import date

from activation_engine_utils import rank_prompts

import aiofiles

from config import PROMPTS_FILE, ENCODING

_prompts_cache: dict = {"data": None, "mtime": None}
_prompts_lock = asyncio.Lock()


async def load_prompts() -> dict:
    """Load and cache journal prompts from ``PROMPTS_FILE``.

    The cache automatically invalidates when ``PROMPTS_FILE`` changes on disk.
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
                    _prompts_cache["data"] = json.loads(prompts_text)
                    _prompts_cache["mtime"] = mtime
                except (FileNotFoundError, json.JSONDecodeError):
                    _prompts_cache["data"] = {}
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
    """Select and return a prompt for the current day."""
    today = date.today()
    weekday = today.strftime("%A")
    season = get_season(today)

    prompts = await load_prompts()
    if not prompts:
        return {"category": None, "prompt": "Prompts file not found"}

    categories_dict = prompts.get("categories")
    if not isinstance(categories_dict, dict):
        return {"category": None, "prompt": "No categories found"}

    categories = list(categories_dict.keys())
    if not categories:
        return {"category": None, "prompt": "No categories found"}

    if tags:
        filtered = [c for c in categories if c.lower() in [t.lower() for t in tags]]
        if filtered:
            categories = filtered

    category = random.choice(categories)
    candidates = categories_dict.get(category, [])
    if tags:
        tag_set = {t.lower() for t in tags}
        candidates = [c for c in candidates if any(t in c.lower() for t in tag_set)] or candidates
    if not candidates:
        return {"category": category.capitalize(), "prompt": "No prompts in this category"}

    if tags:
        ranked = await rank_prompts(candidates, tags)
        if ranked:
            candidates = ranked

    prompt_template = random.choice(candidates)
    prompt = prompt_template.replace("{{weekday}}", weekday).replace("{{season}}", season)
    return {"category": category.capitalize(), "prompt": prompt}
