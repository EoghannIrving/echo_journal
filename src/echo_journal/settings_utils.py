"""Helpers for reading and writing ``settings.yaml`` files."""

import importlib
import logging
import os
from pathlib import Path
from typing import Any, Dict

import yaml

# ``settings.yaml`` should live alongside the journal data so that it persists
# outside of the application container.  Store it within a dedicated
# ``.settings`` directory under ``/journals`` by default, but allow the
# location to be overridden via the ``DATA_DIR`` environment variable.  The
# entire path can also be overridden via ``SETTINGS_PATH``.  When the default
# data directory does not contain a settings file we fall back to looking
# inside ``APP_DIR`` so that bundled defaults can be used on first run.
DATA_DIR = Path(os.getenv("DATA_DIR", "/journals"))
APP_DIR = Path(os.getenv("APP_DIR", "/app"))
SETTINGS_PATH = Path(
    os.getenv("SETTINGS_PATH", DATA_DIR / ".settings" / "settings.yaml")
)

logger = logging.getLogger("ej.settings")


def load_settings(path: Path | None = None) -> Dict[str, str]:
    """Return key/value pairs from a YAML settings file."""
    if path is None:
        path = SETTINGS_PATH
    logger.debug("Loading settings from %s", path)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data: Dict[str, Any] = yaml.safe_load(fh) or {}
            # Ensure keys and values are strings
            #
            # ``settings.yaml`` entries should always take precedence over
            # environment variables, even when the value in the file is blank.
            # Previously blank values would be replaced with those from the
            # environment which meant a value supplied via ``.env`` could
            # override an explicit setting in ``settings.yaml``.  To honor the
            # precedence of ``settings.yaml`` we simply coerce values to
            # strings without injecting environment values here.  Any missing
            # keys will continue to fall back to ``os.getenv`` in
            # ``config._get_setting``.
            cleaned: Dict[str, str] = {}
            for k, v in data.items():
                if v is None:
                    cleaned[str(k)] = ""
                elif isinstance(v, bool):
                    cleaned[str(k)] = "true" if v else "false"
                else:
                    cleaned[str(k)] = str(v)
            logger.debug("Loaded settings: %s", cleaned)
            return cleaned
    except FileNotFoundError:
        logger.debug("Settings file %s not found", path)
        if (
            path == SETTINGS_PATH
            and os.getenv("SETTINGS_PATH") is None
            and (APP_DIR / "settings.yaml").exists()
        ):
            fallback = APP_DIR / "settings.yaml"
            logger.debug("Falling back to default settings at %s", fallback)
            with fallback.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
                cleaned: Dict[str, str] = {}
                for k, v in data.items():
                    if v is None:
                        cleaned[str(k)] = ""
                    elif isinstance(v, bool):
                        cleaned[str(k)] = "true" if v else "false"
                    else:
                        cleaned[str(k)] = str(v)
                logger.debug("Loaded default settings: %s", cleaned)
                return cleaned
        logger.warning(
            "No settings file found at %s; using environment variables only", path
        )
        return {}
    except OSError as exc:
        logger.error("Could not read %s: %s", path, exc)
        return {}


def save_settings(values: Dict[str, str], path: Path | None = None) -> Dict[str, str]:
    """Merge ``values`` into the settings file and return updated mapping."""
    if path is None:
        path = SETTINGS_PATH
    logger.debug("Saving settings to %s: %s", path, values)
    data = load_settings(path)
    data.update(values)
    logger.debug("Merged settings: %s", data)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, allow_unicode=True, default_flow_style=False)
    except OSError as exc:
        logger.error("Could not write %s: %s", path, exc)
    else:
        logger.info("Settings written to %s", path)
        if path == SETTINGS_PATH:
            try:
                logger.debug("Reloading configuration module")
                config_module = importlib.import_module("echo_journal.config")
                importlib.reload(config_module)
            except ImportError as exc:  # pragma: no cover - unexpected
                logger.error("Could not reload config: %s", exc)
    return data
