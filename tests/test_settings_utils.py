"""Tests for ``settings_utils`` helpers."""

import yaml

import settings_utils


def test_load_settings_returns_strings(tmp_path):
    """Values loaded from YAML should be returned as strings."""
    p = tmp_path / "settings.yaml"
    p.write_text("A: 1\nB: test\n", encoding="utf-8")
    data = settings_utils.load_settings(p)
    assert data == {"A": "1", "B": "test"}


def test_save_settings_merges(tmp_path):
    """``save_settings`` should merge and persist values."""
    p = tmp_path / "settings.yaml"
    p.write_text("A: a\n", encoding="utf-8")
    result = settings_utils.save_settings({"B": "b"}, p)
    assert result == {"A": "a", "B": "b"}
    assert yaml.safe_load(p.read_text(encoding="utf-8")) == {"A": "a", "B": "b"}
