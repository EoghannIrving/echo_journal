"""Core application paths and configuration constants."""

from pathlib import Path
import os

# Allow overriding important paths via environment variables for easier testing
# and deployment in restricted environments.
APP_DIR = Path(os.getenv("APP_DIR", "/app"))
DATA_DIR = Path(os.getenv("DATA_DIR", "/journals"))
PROMPTS_FILE = Path(os.getenv("PROMPTS_FILE", str(APP_DIR / "prompts.json")))
STATIC_DIR = Path(os.getenv("STATIC_DIR", str(APP_DIR / "static")))
ENCODING = "utf-8"
WORDNIK_API_KEY = os.getenv("WORDNIK_API_KEY")
IMMICH_URL = os.getenv("IMMICH_URL")
IMMICH_API_KEY = os.getenv("IMMICH_API_KEY")
JELLYFIN_URL = os.getenv("JELLYFIN_URL")
JELLYFIN_API_KEY = os.getenv("JELLYFIN_API_KEY")
JELLYFIN_USER_ID = os.getenv("JELLYFIN_USER_ID")

# File logging path - defaults to ``DATA_DIR/echo_journal.log`` but can
# be overridden via the ``LOG_FILE`` environment variable.
LOG_FILE = Path(os.getenv("LOG_FILE", str(DATA_DIR / "echo_journal.log")))
