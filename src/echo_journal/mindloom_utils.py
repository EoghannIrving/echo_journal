"""Helpers for syncing mood and energy with a Mindloom energy log."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

from . import config

logger = logging.getLogger(__name__)

ENERGY_CATEGORY_TO_VALUE = {
    "drained": 1,
    "low": 2,
    "ok": 3,
    "energized": 4,
}

SAD_KEYWORDS = ("sad", "down", "unhappy")
JOY_KEYWORDS = ("joy", "happy", "delight", "excite", "grateful", "energy")
MEH_KEYWORDS = ("meh", "flat", "tired", "drained", "low", "exhausted", "numb", "bleh")
OKAY_KEYWORDS = (
    "ok",
    "okay",
    "calm",
    "focused",
    "steady",
    "neutral",
    "content",
    "balanced",
    "centered",
)


@dataclass(frozen=True)
class MindloomSnapshot:
    """Reflect the latest available data from the Mindloom energy log."""

    mood: str | None
    energy: str | None
    last_entry_date: date | None
    has_today_entry: bool
    enabled: bool
    available: bool


def _resolve_log_path() -> Path | None:
    """Return the configured path to the Mindloom energy log, or ``None``."""

    value = getattr(config, "MINDLOOM_ENERGY_LOG_PATH", None)
    if not value:
        return None
    path = Path(value)
    return path


def _read_entries(path: Path) -> List[Dict[str, Any]]:
    """Read all entries from the YAML log."""

    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or []
    if isinstance(data, list):
        return data
    return []


def _entry_timestamp(entry: Dict[str, Any]) -> datetime | None:
    """Return a timestamp that can be used to find the latest entry."""

    recorded_at = entry.get("recorded_at")
    if isinstance(recorded_at, str):
        try:
            return datetime.fromisoformat(recorded_at)
        except ValueError:
            pass
    entry_date = _parse_entry_date(entry)
    if entry_date:
        return datetime.combine(entry_date, datetime.min.time())
    return None


def _parse_entry_date(entry: Dict[str, Any]) -> date | None:
    """Parse the ``date`` field from a Mindloom log entry."""

    raw = entry.get("date")
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        return None


def _latest_entry(entries: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    """Return the entry with the most recent timestamp."""

    latest: Dict[str, Any] | None = None
    latest_ts: datetime | None = None
    for entry in entries:
        ts = _entry_timestamp(entry)
        if ts is None:
            continue
        if latest_ts is None or ts > latest_ts:
            latest = entry
            latest_ts = ts
    if latest:
        return latest
    if entries:
        return entries[-1]
    return None


def _map_mindloom_mood(raw_mood: str | None) -> str | None:
    """Translate a Mindloom mood label into Echo Journal's vocabulary."""

    if not raw_mood:
        return None
    token = raw_mood.strip().lower()
    if not token:
        return None
    if "doubt" in token:
        return "self-doubt"
    if any(keyword in token for keyword in SAD_KEYWORDS):
        return "sad"
    if any(keyword in token for keyword in JOY_KEYWORDS):
        return "joyful"
    if any(keyword in token for keyword in MEH_KEYWORDS):
        return "meh"
    if any(keyword in token for keyword in OKAY_KEYWORDS):
        return "okay"
    return None


def _map_mindloom_energy(raw_energy: Any) -> str | None:
    """Convert a Mindloom energy value to one of the UI categories."""

    if raw_energy is None:
        return None
    if isinstance(raw_energy, str) and raw_energy.strip() in ENERGY_CATEGORY_TO_VALUE:
        raw_energy_value = ENERGY_CATEGORY_TO_VALUE[raw_energy.strip()]
    else:
        try:
            raw_energy_value = int(raw_energy)
        except (TypeError, ValueError):
            return None
    if raw_energy_value <= 1:
        return "drained"
    if raw_energy_value == 2:
        return "low"
    if raw_energy_value == 3:
        return "ok"
    return "energized"


def _load_snapshot_sync() -> MindloomSnapshot:
    """Read the log and translate the latest snapshot into Echo Journal defaults."""

    log_path = _resolve_log_path()
    if log_path is None:
        return MindloomSnapshot(None, None, None, False, False, False)
    try:
        entries = _read_entries(log_path)
    except (OSError, yaml.YAMLError) as exc:  # pragma: no cover - defensive guard
        logger.warning("Failed to read Mindloom energy log %s: %s", log_path, exc)
        return MindloomSnapshot(None, None, None, False, True, False)
    latest_entry = _latest_entry(entries)
    latest_date = _parse_entry_date(latest_entry) if latest_entry else None
    latest_mood = _map_mindloom_mood(latest_entry.get("mood") if latest_entry else None)
    latest_energy = _map_mindloom_energy(
        latest_entry.get("energy") if latest_entry else None
    )
    today = date.today()
    has_today = any(_parse_entry_date(entry) == today for entry in entries)
    return MindloomSnapshot(
        mood=latest_mood,
        energy=latest_energy,
        last_entry_date=latest_date,
        has_today_entry=has_today,
        enabled=True,
        available=True,
    )


def _energy_category_to_value(category: str) -> int | None:
    """Return the numeric energy level that corresponds to a UI choice."""

    if not category:
        return None
    return ENERGY_CATEGORY_TO_VALUE.get(category.strip().lower())


def _normalize_mood_for_recording(mood: str) -> str:
    """Format the mood label in the style of existing Mindloom entries."""

    return mood.strip().title()


def _record_entry_if_missing_sync(mood: str, energy: str) -> bool:
    """Append an entry for today when the log lacks one."""

    if not mood or not energy:
        return False
    log_path = _resolve_log_path()
    if log_path is None:
        return False
    try:
        entries = _read_entries(log_path)
    except (OSError, yaml.YAMLError) as exc:  # pragma: no cover - defensive guard
        logger.warning("Unable to read Mindloom log before writing: %s", exc)
        return False
    today = date.today()
    if any(_parse_entry_date(entry) == today for entry in entries):
        logger.debug("Mindloom already has an entry for %s", today)
        return False
    energy_value = _energy_category_to_value(energy)
    if energy_value is None:
        logger.debug("Skipping Mindloom record: unknown energy %s", energy)
        return False
    new_entry: Dict[str, Any] = {
        "date": today.isoformat(),
        "energy": energy_value,
        "mood": _normalize_mood_for_recording(mood),
        "recorded_at": datetime.now().isoformat(),
    }
    sanitized_entries = entries.copy()
    sanitized_entries.append(new_entry)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        yaml.dump(sanitized_entries, handle, allow_unicode=True, sort_keys=False)
    logger.info("Recorded Mindloom entry for %s", today)
    return True


async def load_snapshot() -> MindloomSnapshot:
    """Return the latest Mindloom snapshot without blocking the event loop."""

    return await asyncio.to_thread(_load_snapshot_sync)


async def record_entry_if_missing(mood: str, energy: str) -> bool:
    """Record today's mood/energy back to Mindloom if no entry exists yet."""

    return await asyncio.to_thread(_record_entry_if_missing_sync, mood, energy)
