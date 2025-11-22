"""Unit tests for the Mindloom integration helpers."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

import yaml

from echo_journal import config, mindloom_utils


def _write_entries(path, entries):
    path.write_text(yaml.safe_dump(entries, sort_keys=False), encoding="utf-8")


def test_load_snapshot_reads_latest(tmp_path, monkeypatch):
    """Load snapshot should map the most recent entry to Echo Journal defaults."""

    target_path = tmp_path / "mindloom_energy.yaml"
    entries = [
        {
            "date": (date.today() - timedelta(days=2)).isoformat(),
            "energy": 4,
            "mood": "Joyful",
        },
        {
            "date": (date.today() - timedelta(days=1)).isoformat(),
            "energy": 2,
            "mood": "Tired",
        },
    ]
    _write_entries(target_path, entries)
    monkeypatch.setattr(config, "MINDLOOM_ENERGY_LOG_PATH", target_path)
    snapshot = asyncio.run(mindloom_utils.load_snapshot())
    assert snapshot.mood == "meh"
    assert snapshot.energy == "low"
    assert snapshot.last_entry_date == date.today() - timedelta(days=1)
    assert not snapshot.has_today_entry


def test_load_snapshot_weights_today_entries(tmp_path, monkeypatch):
    """Bucketed recency should show a weighted average for today’s data."""

    target_path = tmp_path / "mindloom_energy.yaml"
    today = date.today()
    entries = [
        {
            "date": (today - timedelta(days=1)).isoformat(),
            "energy": 1,
            "mood": "Sad",
        },
        {
            "date": today.isoformat(),
            "energy": 3,
            "mood": "Content",
            "recorded_at": f"{today.isoformat()}T08:45:00",
        },
        {
            "date": today.isoformat(),
            "energy": 4,
            "mood": "Joyful",
            "recorded_at": f"{today.isoformat()}T20:15:00",
        },
    ]
    _write_entries(target_path, entries)
    monkeypatch.setattr(config, "MINDLOOM_ENERGY_LOG_PATH", target_path)
    snapshot = asyncio.run(mindloom_utils.load_snapshot())
    assert snapshot.mood == "joyful"
    assert snapshot.energy == "energized"
    assert snapshot.has_today_entry


def test_record_entry_if_missing_appends_only_once(tmp_path, monkeypatch):
    """Recording should append today if no entry exists yet and avoid duplicates."""

    target_path = tmp_path / "mindloom_energy.yaml"
    monkeypatch.setattr(config, "MINDLOOM_ENERGY_LOG_PATH", target_path)
    first = asyncio.run(mindloom_utils.record_entry_if_missing("joyful", "energized"))
    assert first is True
    entries = yaml.safe_load(target_path.read_text(encoding="utf-8")) or []
    assert len(entries) == 1
    today_entry = entries[0]
    assert today_entry["date"] == date.today().isoformat()
    assert today_entry["energy"] == 4
    assert today_entry["mood"] == "Joyful"
    second = asyncio.run(mindloom_utils.record_entry_if_missing("joyful", "energized"))
    assert second is False
    entries = yaml.safe_load(target_path.read_text(encoding="utf-8")) or []
    assert len(entries) == 1
