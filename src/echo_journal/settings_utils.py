"""Helpers for reading and writing ``settings.yaml`` files."""

import logging
import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

load_dotenv()

# ``settings.yaml`` should live alongside the journal data so that it persists
# outside of the application container.  Default to ``/journals`` but allow the
# location to be overridden via the ``DATA_DIR`` environment variable.
DATA_DIR = Path(os.getenv("DATA_DIR", "/journals"))
SETTINGS_PATH = DATA_DIR / "settings.yaml"

logger = logging.getLogger("ej.settings")


def load_settings(path: Path | None = None) -> Dict[str, str]:
    """Return key/value pairs from a YAML settings file."""
    if path is None:
        path = SETTINGS_PATH
    try:
        with path.open("r", encoding="utf-8") as fh:
            data: Dict[str, Any] = yaml.safe_load(fh) or {}
            # Ensure keys and values are strings
            return {str(k): str(v) for k, v in data.items()}
    except OSError as exc:
        logger.error("Could not read %s: %s", path, exc)
        return {}


def save_settings(values: Dict[str, str], path: Path | None = None) -> Dict[str, str]:
    """Merge ``values`` into the settings file and return updated mapping."""
    if path is None:
        path = SETTINGS_PATH
    data = load_settings(path)
    data.update(values)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, allow_unicode=True, default_flow_style=False)
    except OSError as exc:
        logger.error("Could not write %s: %s", path, exc)
    return data
