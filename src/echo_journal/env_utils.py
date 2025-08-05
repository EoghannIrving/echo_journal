"""Helpers for reading .env files."""

import logging
import os
import shlex
from pathlib import Path
from typing import Dict


# Absolute path to the project's ``.env`` file. It can be overridden with the
# ``ECHO_JOURNAL_ENV_PATH`` environment variable so that calls from any working
# directory can locate the file.
ENV_PATH = Path(
    os.environ.get(
        "ECHO_JOURNAL_ENV_PATH",
        Path(__file__).resolve().parents[2] / ".env",
    )
).expanduser().resolve()

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
                if not line or line.startswith("#"):
                    continue
                for token in shlex.split(line, comments=True, posix=True):
                    if "=" not in token:
                        continue
                    key, value = token.split("=", 1)
                    env[key] = value
    except OSError as exc:
        logger.error("Could not read %s: %s", path, exc)
    return env
