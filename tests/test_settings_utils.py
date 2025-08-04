"""Tests for ``settings_utils`` helpers."""

import importlib
import logging

import yaml

from echo_journal import config, settings_utils


def test_load_settings_returns_strings(tmp_path):
    """Values loaded from YAML should be returned as strings."""
    p = tmp_path / "settings.yaml"
    p.write_text("A: 1\nB: test\n", encoding="utf-8")
    data = settings_utils.load_settings(p)
    assert data == {"A": "1", "B": "test"}


def test_load_settings_uses_env_for_blank_values(tmp_path, monkeypatch):
    """Blank values in settings should fall back to environment variables."""
    p = tmp_path / "settings.yaml"
    p.write_text("A:\nB: existing\n", encoding="utf-8")
    monkeypatch.setenv("A", "from_env")
    data = settings_utils.load_settings(p)
    assert data == {"A": "from_env", "B": "existing"}


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


def test_save_settings_creates_dir(tmp_path, caplog):
    """Missing parent directories should be created when saving settings."""
    p = tmp_path / "dir" / "settings.yaml"
    with caplog.at_level(logging.ERROR, logger="ej.settings"):
        data = settings_utils.save_settings({"A": "1"}, p)
    assert data == {"A": "1"}
    assert yaml.safe_load(p.read_text(encoding="utf-8")) == {"A": "1"}
    # No error logs expected
    assert all("Could not write" not in r.getMessage() for r in caplog.records)


def test_settings_path_relative_to_data_dir(tmp_path, monkeypatch):
    """Default ``SETTINGS_PATH`` should live under ``DATA_DIR``."""
    data_dir = tmp_path / "data"
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    importlib.reload(settings_utils)
    settings_utils.save_settings({"X": "1"})
    expected = data_dir / "settings.yaml"
    assert expected.read_text(encoding="utf-8") == "X: '1'\n"
    # Reset module to default state for other tests
    monkeypatch.delenv("DATA_DIR")
    importlib.reload(settings_utils)


def test_save_settings_reloads_config(tmp_path, monkeypatch):
    """Saving to the default path should reload the configuration module."""
    settings_file = tmp_path / "settings.yaml"
    orig_path = settings_utils.SETTINGS_PATH
    monkeypatch.setattr(settings_utils, "SETTINGS_PATH", settings_file)

    importlib.reload(config)
    assert config.WORDNIK_API_KEY is None

    settings_utils.save_settings({"WORDNIK_API_KEY": "abc"})
    assert config.WORDNIK_API_KEY == "abc"

    # Reset modules for subsequent tests
    monkeypatch.setattr(settings_utils, "SETTINGS_PATH", orig_path)
    importlib.reload(config)
