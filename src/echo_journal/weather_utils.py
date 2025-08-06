"""Helpers for building frontmatter with optional weather data."""

from typing import Optional, Dict
from datetime import datetime

import httpx
import yaml

from .wordnik_utils import fetch_word_of_day


async def fetch_weather(lat: float, lon: float) -> Optional[str]:
    """Fetch current weather description from Open-Meteo."""
    if lat == 0 and lon == 0:
        return None
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "current_weather": True}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            cw = data.get("current_weather", {})
            temp = cw.get("temperature")
            code = cw.get("weathercode")
            if temp is not None and code is not None:
                return f"{temp}°C code {code}"
    except (httpx.HTTPError, ValueError):
        return None
    return None


def time_of_day_label(now: datetime | None = None) -> str:
    """Return Morning/Afternoon/Evening/Night for the given time."""
    dt = now or datetime.now()
    hour = dt.hour
    if 5 <= hour < 12:
        return "Morning"
    if 12 <= hour < 17:
        return "Afternoon"
    if 17 <= hour < 21:
        return "Evening"
    return "Night"


async def build_frontmatter(
    location: dict,
    weather: Optional[Dict[str, float]] = None,
    integrations: dict | None = None,
) -> str:
    """Return a YAML frontmatter string based on the provided location and weather.

    ``integrations`` toggles optional data sources like Wordnik and Immich.
    """
    integrations = integrations or {}
    lat = float(location.get("lat") or 0)
    lon = float(location.get("lon") or 0)
    label = location.get("label") or ""
    if weather and "temperature" in weather and "code" in weather:
        weather_str = f"{weather['temperature']}°C code {int(weather['code'])}"
    else:
        weather_str = await fetch_weather(lat, lon)
    wotd_word = wotd_def = None
    if integrations.get("wordnik", True):
        wotd = await fetch_word_of_day()
        if wotd:
            wotd_word, wotd_def = wotd

    lines = []
    if label:
        lines.append(f"location: {label}")
    if weather_str:
        lines.append(f"weather: {weather_str}")
    lines.append(f"save_time: {time_of_day_label()}")
    if wotd_word:
        lines.append(f"wotd: {wotd_word}")
        if wotd_def:
            dumped_lines = (
                yaml.safe_dump(wotd_def, explicit_end=False).strip().splitlines()
            )
            dumped = " ".join(
                line.strip()
                for line in dumped_lines
                if line.strip() and line.strip() != "..."
            )
            lines.append(f"wotd_def: {dumped}")
    if integrations.get("immich", True):
        lines.append("photos: []")
    return "\n".join(lines)
