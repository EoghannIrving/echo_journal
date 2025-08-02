"""Core application paths and configuration constants."""

from pathlib import Path
import os

# Allow overriding important paths via environment variables for easier testing
# and deployment in restricted environments.
APP_DIR = Path(os.getenv("APP_DIR", "/app"))
DATA_DIR = Path(os.getenv("DATA_DIR", "/journals"))
PROMPTS_FILE = Path(os.getenv("PROMPTS_FILE", str(APP_DIR / "prompts.yaml")))
STATIC_DIR = Path(os.getenv("STATIC_DIR", str(APP_DIR / "static")))
TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", str(APP_DIR / "templates")))
ENCODING = "utf-8"
WORDNIK_API_KEY = os.getenv("WORDNIK_API_KEY")
IMMICH_URL = os.getenv("IMMICH_URL")
IMMICH_API_KEY = os.getenv("IMMICH_API_KEY")
JELLYFIN_URL = os.getenv("JELLYFIN_URL")
JELLYFIN_API_KEY = os.getenv("JELLYFIN_API_KEY")
JELLYFIN_USER_ID = os.getenv("JELLYFIN_USER_ID")
JELLYFIN_PLAY_THRESHOLD = int(os.getenv("JELLYFIN_PLAY_THRESHOLD", "90"))
ACTIVATION_ENGINE_URL = os.getenv("ACTIVATION_ENGINE_URL", "http://localhost:8000")

# File logging path - defaults to ``DATA_DIR/echo_journal.log`` but can
# be overridden via the ``LOG_FILE`` environment variable.
LOG_FILE = Path(os.getenv("LOG_FILE", str(DATA_DIR / "echo_journal.log")))

# Log level for the application. Defaults to ``DEBUG`` so development
# environments capture detailed output, but can be overridden to
# ``INFO`` or ``WARNING`` in production.
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()

# Maximum bytes before the log file is rotated. A few megabytes keeps
# logs manageable while still retaining recent history.
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(1_048_576)))

# Number of rotated log files to keep.
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "3"))

# Optional HTTP Basic auth credentials. If both are set, requests must
# include matching Authorization headers. When unset, authentication is
# disabled.
BASIC_AUTH_USERNAME = os.getenv("BASIC_AUTH_USERNAME")
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD")
