"""Utility functions for reading and parsing journal entries."""

from pathlib import Path
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import aiofiles
import yaml

from . import config


def safe_entry_path(entry_date: str, data_dir: Path | None = None) -> Path:
    """Return a normalized path for the given entry date inside ``data_dir``."""
    if data_dir is None:
        data_dir = config.DATA_DIR
    sanitized = Path(entry_date).name
    sanitized = re.sub(r"[^0-9A-Za-z_-]", "_", sanitized)
    if not sanitized:
        raise ValueError("Invalid entry date")
    try:
        datetime.strptime(sanitized, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Invalid entry date") from exc
    path = (data_dir / sanitized).with_suffix(".md")
    # Ensure the path cannot escape ``data_dir``
    try:
        path.resolve().relative_to(data_dir.resolve())
    except ValueError as exc:
        raise ValueError("Invalid entry date") from exc
    return path


def parse_entry(md_content: str) -> Tuple[str, str]:
    """Return (prompt, entry) sections from markdown without raising errors."""
    prompt_lines: List[str] = []
    entry_lines: List[str] = []
    current_section = None
    for line in md_content.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered == "# prompt":
            current_section = "prompt"
            continue
        if lowered == "# entry":
            current_section = "entry"
            continue
        if current_section == "prompt":
            prompt_lines.append(line.rstrip())
        elif current_section == "entry":
            entry_lines.append(line.rstrip())

    prompt = "\n".join(prompt_lines)
    entry = "\n".join(entry_lines)
    return prompt, entry


def split_frontmatter(text: str) -> Tuple[Optional[str], str]:
    """Return frontmatter and remaining content if present."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1].strip()
            body = parts[2].lstrip("\n")
            return fm, body
    return None, text


async def read_existing_frontmatter(file_path: Path) -> Optional[str]:
    """Return frontmatter from the given file path if present."""
    try:
        async with aiofiles.open(file_path, "r", encoding=config.ENCODING) as fh:
            existing = await fh.read()
        frontmatter, _ = split_frontmatter(existing)
        return frontmatter
    except OSError:
        return None


def parse_frontmatter(frontmatter: str) -> Dict[str, Any]:
    """Return a dictionary parsed from YAML frontmatter."""
    try:
        data = yaml.safe_load(frontmatter) or {}
    except yaml.YAMLError:
        return {}
    if isinstance(data, dict):
        return data
    return {}


async def load_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """Return parsed JSON data from ``file_path`` or an empty list."""
    if not file_path.exists():
        return []
    try:
        async with aiofiles.open(file_path, "r", encoding=config.ENCODING) as fh:
            return json.loads(await fh.read())
    except (OSError, ValueError):
        return []


WEATHER_CODES = {
    0: ("☀️", "Clear"),
    1: ("🌤️", "Mostly clear"),
    2: ("⛅", "Partly cloudy"),
    3: ("☁️", "Overcast"),
    45: ("🌫️", "Fog"),
    48: ("🌫️", "Fog"),
    51: ("🌦️", "Drizzle"),
    53: ("🌦️", "Drizzle"),
    55: ("🌦️", "Drizzle"),
    61: ("🌧️", "Rain"),
    63: ("🌧️", "Rain"),
    65: ("🌧️", "Heavy rain"),
    71: ("❄️", "Snow"),
    73: ("❄️", "Snow"),
    75: ("❄️", "Snow"),
    80: ("🌦️", "Showers"),
    81: ("🌦️", "Showers"),
    82: ("🌧️", "Heavy showers"),
    95: ("⛈️", "Thunderstorm"),
    96: ("⛈️", "Thunderstorm"),
    99: ("⛈️", "Thunderstorm"),
}


def format_weather(weather: str) -> str:
    """Return only the weather icon from ``weather`` frontmatter."""
    match = re.search(r"(-?\d+(?:\.\d+)?)°C code (\d+)", weather)
    if not match:
        return weather
    code = int(match.group(2))
    icon, _ = WEATHER_CODES.get(code, ("", ""))
    return icon


def weather_description(weather: str) -> str:
    """Return a textual description and temperature from ``weather`` frontmatter."""
    match = re.search(r"(-?\d+(?:\.\d+)?)°C code (\d+)", weather)
    if not match:
        return weather
    temp = match.group(1)
    code = int(match.group(2))
    _, desc = WEATHER_CODES.get(code, ("", ""))
    if desc:
        return f"{desc}, {temp}°C"
    return f"{temp}°C"
