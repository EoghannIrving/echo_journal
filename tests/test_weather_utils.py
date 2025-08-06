"""Tests for weather utility helpers."""

# pylint: disable=missing-function-docstring,missing-class-docstring,unused-argument,duplicate-code

import asyncio
from datetime import datetime

import yaml

from echo_journal import weather_utils


class FakeClient:
    """Minimal ``httpx.AsyncClient`` stand-in for ``fetch_weather``."""

    def __init__(self, data):
        self._data = data
        self.captured = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None, timeout=None):
        self.captured["url"] = url
        self.captured["params"] = params

        class Response:
            def __init__(self, data):
                self._data = data

            def raise_for_status(self):
                return None

            def json(self):
                return self._data

        return Response(self._data)


def test_fetch_weather(monkeypatch):
    """Successful requests should yield a formatted weather string."""
    client = FakeClient({"current_weather": {"temperature": 12, "weathercode": 3}})
    monkeypatch.setattr(weather_utils.httpx, "AsyncClient", lambda: client)
    weather = asyncio.run(weather_utils.fetch_weather(1, 2))
    assert weather == "12\u00b0C code 3"
    assert client.captured["params"]["latitude"] == 1


def test_fetch_weather_zero():
    """Lat/Lon of zero should short-circuit to ``None``."""
    assert asyncio.run(weather_utils.fetch_weather(0, 0)) is None


def test_time_of_day_label():
    """Time ranges should map to labels."""
    assert weather_utils.time_of_day_label(datetime(2024, 1, 1, 6)) == "Morning"
    assert weather_utils.time_of_day_label(datetime(2024, 1, 1, 13)) == "Afternoon"
    assert weather_utils.time_of_day_label(datetime(2024, 1, 1, 18)) == "Evening"
    assert weather_utils.time_of_day_label(datetime(2024, 1, 1, 23)) == "Night"


def test_build_frontmatter(monkeypatch):
    """Frontmatter should include location, weather and word of the day."""

    async def fake_fetch_weather(lat, lon):
        return "10\u00b0C code 2"

    async def fake_wotd():
        return ("word", "definition")

    monkeypatch.setattr(weather_utils, "fetch_weather", fake_fetch_weather)
    monkeypatch.setattr(weather_utils, "fetch_word_of_day", fake_wotd)
    monkeypatch.setattr(weather_utils, "time_of_day_label", lambda: "Morning")
    fm = asyncio.run(
        weather_utils.build_frontmatter(
            {"lat": 1, "lon": 2, "label": "Town"},
            integrations={"immich": False},
        )
    )
    lines = fm.splitlines()
    assert "location: Town" in lines
    assert "weather: 10\u00b0C code 2" in lines
    assert "wotd: word" in lines
    assert "wotd_def: definition" in lines
    assert all("photos" not in line for line in lines)


def test_build_frontmatter_multiline_definition(monkeypatch):
    """Multi-line definitions should be preserved in full."""

    async def fake_fetch_weather(lat, lon):
        return "10\u00b0C code 2"

    async def fake_wotd():
        return ("word", "first line\nsecond line")

    monkeypatch.setattr(weather_utils, "fetch_weather", fake_fetch_weather)
    monkeypatch.setattr(weather_utils, "fetch_word_of_day", fake_wotd)
    monkeypatch.setattr(weather_utils, "time_of_day_label", lambda: "Morning")

    fm = asyncio.run(
        weather_utils.build_frontmatter(
            {"lat": 1, "lon": 2, "label": "Town"},
            integrations={"immich": False},
        )
    )
    parsed = yaml.safe_load(fm)
    assert parsed["wotd_def"] == "first line second line"
