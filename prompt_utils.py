"""Prompt loading and generation helpers."""

import asyncio
import json
import random
from datetime import date
from typing import Optional

import aiofiles

from config import PROMPTS_FILE, ENCODING

_prompts_cache: Optional[dict] = None
_prompts_lock = asyncio.Lock()


async def load_prompts() -> dict:
    """Load and cache journal prompts from PROMPTS_FILE."""
    global _prompts_cache
    if _prompts_cache is None:
        async with _prompts_lock:
            if _prompts_cache is None:
                try:
                    async with aiofiles.open(PROMPTS_FILE, "r", encoding=ENCODING) as fh:
                        prompts_text = await fh.read()
                    _prompts_cache = json.loads(prompts_text)
                except (FileNotFoundError, json.JSONDecodeError):
                    _prompts_cache = {}
    return _prompts_cache


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


async def generate_prompt() -> dict:
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

    category = random.choice(categories)
    candidates = categories_dict.get(category, [])
    if not candidates:
        return {"category": category.capitalize(), "prompt": "No prompts in this category"}

    prompt_template = random.choice(candidates)
    prompt = prompt_template.replace("{{weekday}}", weekday).replace("{{season}}", season)
    return {"category": category.capitalize(), "prompt": prompt}
