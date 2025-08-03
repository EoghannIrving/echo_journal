"""Tests for configuration helpers."""

# pylint: disable=protected-access

from echo_journal import config


def test_get_setting_prefers_settings(monkeypatch):
    """Values in ``_SETTINGS`` should override environment variables."""
    monkeypatch.setattr(config, "_SETTINGS", {"A": "from_settings"})
    monkeypatch.setenv("A", "from_env")
    assert config._get_setting("A") == "from_settings"


def test_get_setting_env(monkeypatch):
    """Environment variables are used when not in settings."""
    monkeypatch.setattr(config, "_SETTINGS", {})
    monkeypatch.setenv("B", "env_val")
    assert config._get_setting("B", "def") == "env_val"


def test_get_setting_default(monkeypatch):
    """Default value is returned when key missing everywhere."""
    monkeypatch.setattr(config, "_SETTINGS", {})
    monkeypatch.delenv("C", raising=False)
    assert config._get_setting("C", "def") == "def"
