"""Helpers for reading and writing .env files."""

import logging
from pathlib import Path
from typing import Dict

ENV_PATH = Path(".env")

logger = logging.getLogger("ej.env")


def load_env(path: Path | None = None) -> Dict[str, str]:
    """Return key/value pairs from a .env file."""
    if path is None:
        path = ENV_PATH
    env: Dict[str, str] = {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    except OSError as exc:
        logger.error("Could not read %s: %s", path, exc)
    return env


def save_env(values: Dict[str, str], path: Path | None = None) -> Dict[str, str]:
    """Merge ``values`` into the .env file and return updated mapping."""
    if path is None:
        path = ENV_PATH
    data = load_env(path)
    data.update(values)
    lines = [f"{k}={v}" for k, v in data.items()]
    content = "\n".join(lines) + "\n"
    try:
        with path.open("w", encoding="utf-8") as fh:
            fh.write(content)
    except OSError as exc:
        logger.error("Could not write %s: %s", path, exc)
    return data
