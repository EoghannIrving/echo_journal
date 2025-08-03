"""Tests for ``settings_utils`` helpers."""

import logging
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


def test_load_settings_logs_error(tmp_path, caplog):
    """Missing files should log an error and return an empty dict."""
    p = tmp_path / "missing.yaml"
    with caplog.at_level(logging.ERROR, logger="ej.settings"):
        data = settings_utils.load_settings(p)
    assert data == {}
    assert any(str(p) in r.getMessage() for r in caplog.records)


def test_save_settings_logs_error(tmp_path, caplog):
    """Errors writing settings files should be logged."""
    p = tmp_path / "dir" / "settings.yaml"
    with caplog.at_level(logging.ERROR, logger="ej.settings"):
        data = settings_utils.save_settings({"A": "1"}, p)
    assert data == {"A": "1"}
    assert any(str(p) in r.getMessage() for r in caplog.records)
