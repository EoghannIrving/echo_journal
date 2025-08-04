"""Core application paths and configuration constants."""

from pathlib import Path
import os

from .settings_utils import load_settings

_SETTINGS = load_settings()


def _get_setting(key: str, default: str | None = None) -> str | None:
    """Return a configuration value from settings.yaml overriding environment variables.

    Empty strings in either source are treated as missing values so the
    provided ``default`` is used instead. This prevents downstream code from
    receiving empty strings when it expects ``None`` or a usable value.
    """
    value = _SETTINGS.get(key)
    if value in (None, ""):
        value = os.getenv(key, default)
    if value == "":
        return default
    return value

# Allow overriding important paths via environment variables for easier testing
# and deployment in restricted environments.
APP_DIR = Path(_get_setting("APP_DIR", "/app"))
DATA_DIR = Path(_get_setting("DATA_DIR", "/journals"))
PROMPTS_FILE = Path(_get_setting("PROMPTS_FILE", str(APP_DIR / "prompts.yaml")))
STATIC_DIR = Path(_get_setting("STATIC_DIR", str(APP_DIR / "static")))
TEMPLATES_DIR = Path(_get_setting("TEMPLATES_DIR", str(APP_DIR / "templates")))
ENCODING = "utf-8"
WORDNIK_API_KEY = _get_setting("WORDNIK_API_KEY")
OPENAI_API_KEY = _get_setting("OPENAI_API_KEY")
IMMICH_URL = _get_setting("IMMICH_URL")
IMMICH_API_KEY = _get_setting("IMMICH_API_KEY")
IMMICH_TIME_BUFFER = int(_get_setting("IMMICH_TIME_BUFFER", "15"))
JELLYFIN_URL = _get_setting("JELLYFIN_URL")
JELLYFIN_API_KEY = _get_setting("JELLYFIN_API_KEY")
JELLYFIN_USER_ID = _get_setting("JELLYFIN_USER_ID")
JELLYFIN_PAGE_SIZE = int(_get_setting("JELLYFIN_PAGE_SIZE", "200"))
JELLYFIN_PLAY_THRESHOLD = int(_get_setting("JELLYFIN_PLAY_THRESHOLD", "90"))
NOMINATIM_USER_AGENT = _get_setting(
    "NOMINATIM_USER_AGENT", "EchoJournal/1.0 (contact@example.com)"
)

# File logging path - defaults to ``DATA_DIR/.logs/echo_journal.log`` but can
# be overridden via the ``LOG_FILE`` environment variable.
LOG_FILE = Path(
    _get_setting("LOG_FILE", str(DATA_DIR / ".logs" / "echo_journal.log"))
)

# Log level for the application. Defaults to ``DEBUG`` so development
# environments capture detailed output, but can be overridden to
# ``INFO`` or ``WARNING`` in production.
LOG_LEVEL = _get_setting("LOG_LEVEL", "DEBUG").upper()

# Maximum bytes before the log file is rotated. A few megabytes keeps
# logs manageable while still retaining recent history.
LOG_MAX_BYTES = int(_get_setting("LOG_MAX_BYTES", str(1_048_576)))

# Number of rotated log files to keep.
LOG_BACKUP_COUNT = int(_get_setting("LOG_BACKUP_COUNT", "3"))

# Optional HTTP Basic auth credentials. If both are set, requests must
# include matching Authorization headers. When unset, authentication is
# disabled.
BASIC_AUTH_USERNAME = _get_setting("BASIC_AUTH_USERNAME")
BASIC_AUTH_PASSWORD = _get_setting("BASIC_AUTH_PASSWORD")
