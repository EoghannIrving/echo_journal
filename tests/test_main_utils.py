"""Tests for helper functions in ``main``."""

# pylint: disable=protected-access

from datetime import date
import importlib

import main


def test_with_updated_save_time_replaces_indented():
    """Existing save_time with indentation should be replaced, not duplicated."""
    fm = "  save_time: Morning\nother: x"
    updated = main._with_updated_save_time(fm, "Evening")
    lines = updated.splitlines()
    assert lines[0] == "  save_time: Evening"
    assert lines[1] == "other: x"
    assert updated.count("save_time:") == 1


def test_calculate_streaks_deduplicates_dates(tmp_path, monkeypatch):
    """Duplicate entry dates should not inflate streak counts."""

    monkeypatch.setenv("APP_DIR", str(tmp_path))
    (tmp_path / "static").mkdir()
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "static"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TEMPLATES_DIR", str(tmp_path))
    monkeypatch.setenv("PROMPTS_FILE", str(tmp_path / "prompts.json"))

    mod = importlib.reload(main)

    dates = [
        date(2022, 1, 1),
        date(2022, 1, 1),
        date(2022, 1, 2),
        date(2022, 1, 3),
        date(2022, 1, 3),
    ]

    streaks = mod._calculate_streaks(dates)

    assert streaks == {
        "current_day_streak": 3,
        "longest_day_streak": 3,
        "current_week_streak": 2,
        "longest_week_streak": 2,
    }
