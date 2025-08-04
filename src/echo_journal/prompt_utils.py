"""Prompt loading and generation helpers."""

import asyncio
import random
from datetime import date

import yaml
import aiofiles
import logging

from .config import PROMPTS_FILE, ENCODING

_prompts_cache: dict = {"data": None, "mtime": None}
_prompts_lock = asyncio.Lock()

logger = logging.getLogger("ej.prompt")

# Mapping of anchor types to (mood, energy) pairs
ANCHOR_MOOD_ENERGY: dict[str, list[tuple[str, int]]] = {
    "soft": [
        ("sad", 1), ("meh", 1), ("drained", 1), ("self-doubt", 1),
        ("self-doubt", 2), ("okay", 2),
    ],
    "moderate": [
        ("meh", 2), ("okay", 3), ("joyful", 3), ("self-doubt", 3),
        ("focused", 3), ("energized", 3),
    ],
    "strong": [
        ("joyful", 4), ("focused", 4), ("energized", 4),
    ],
    "micro": [
        ("sad", 1), ("drained", 1), ("self-doubt", 1),
    ],
}


def _choose_anchor(mood: str | None, energy: int | None) -> str | None:
    """Return a random anchor value based on mood and energy."""
    if mood is None or energy is None:
        logger.debug("No anchor: mood=%s energy=%s", mood, energy)
        return None
    mood_l = mood.lower()
    matches = [
        anchor
        for anchor, pairs in ANCHOR_MOOD_ENERGY.items()
        if (mood_l, energy) in pairs
    ]
    if not matches:
        logger.debug("No anchor matches for mood=%s energy=%s", mood_l, energy)
        return None
    anchor = random.choice(matches)
    logger.debug(
        "Selected anchor '%s' for mood=%s energy=%s from %s",
        anchor,
        mood_l,
        energy,
        matches,
    )
    return anchor


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


async def generate_prompt(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    mood: str | None = None,
    energy: int | None = None,
    debug: bool = False,
) -> dict:
    """Select and return a prompt for the current day.

    ``mood`` and ``energy`` are used only to derive an ``anchor`` value via
    :data:`ANCHOR_MOOD_ENERGY`. Prompts are filtered solely by this anchor. If
    ``debug`` is ``True``, information about the selection process is returned
    under a ``debug`` key.
    """
    logger.debug("Generating prompt for mood=%s energy=%s", mood, energy)
    today = date.today()
    weekday = today.strftime("%A")
    season = get_season(today)

    prompts = await load_prompts()
    logger.debug("Loaded %d prompts", len(prompts) if isinstance(prompts, list) else 0)
    if not isinstance(prompts, list) or not prompts:
        result = {"category": None, "prompt": "Prompts file not found"}
        if debug:
            result["debug"] = {
                "initial": [],
                "after_anchor": [],
                "chosen": None,
            }
        return result

    candidates = prompts
    logger.debug("Initial candidates: %s", [p.get("id") for p in candidates])
    debug_info: dict[str, object] = {}
    if debug:
        debug_info["initial"] = [p.get("id") for p in candidates]

    anchor = _choose_anchor(mood, energy)
    logger.debug("Anchor after choice: %s", anchor)
    if anchor:
        candidates = [p for p in candidates if p.get("anchor") == anchor]
        if debug:
            debug_info["after_anchor"] = [p.get("id") for p in candidates]
        logger.debug("Candidates after anchor filter: %s", [p.get("id") for p in candidates])
    elif debug:
        debug_info["after_anchor"] = [p.get("id") for p in candidates]

    if not candidates:
        result = {"category": None, "prompt": "No prompts available"}
        if debug:
            debug_info["chosen"] = None
            result["debug"] = debug_info
        return result

    chosen = random.choice(candidates)
    logger.debug("Chosen prompt: %s", chosen.get("id"))
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
    if debug:
        debug_info["chosen"] = pid
        result["debug"] = debug_info
    logger.debug(
        "Result prompt id=%s category=%s anchor=%s",
        pid,
        result.get("category"),
        result.get("anchor"),
    )
    return result
