"""Helpers for reading and writing settings.yaml files."""

import logging
from pathlib import Path
from typing import Dict, Any

import yaml

SETTINGS_PATH = Path("settings.yaml")

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
        with path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, allow_unicode=True, default_flow_style=False)
    except OSError as exc:
        logger.error("Could not write %s: %s", path, exc)
    return data
