"""Helpers for building frontmatter with optional weather data."""

from typing import Optional
from datetime import datetime

import httpx


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


async def build_frontmatter(location: dict) -> str:
    """Return a YAML frontmatter string based on the provided location."""
    lat = float(location.get("lat") or 0)
    lon = float(location.get("lon") or 0)
    label = location.get("label") or ""
    weather = await fetch_weather(lat, lon)

    lines = []
    if label:
        lines.append(f"location: {label}")
    if weather:
        lines.append(f"weather: {weather}")
    lines.append(f"save_time: {time_of_day_label()}")
    lines.append("photos: []")
    return "\n".join(lines)
