"""Core application paths and configuration constants."""

import os
from pathlib import Path
from typing import overload

from .env_utils import load_env as _load_env
from .settings_utils import load_settings


def _load_dotenv() -> None:
    """Merge values from the .env file into os.environ without overriding existing keys.

    The test suite should not be affected by developer .env files, so
    loading is skipped when running under pytest.
    """
    # Skip loading developer .env when running under pytest
    import sys

    if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
        return
    for key, value in _load_env().items():
        os.environ.setdefault(key, value)


_load_dotenv()

_SETTINGS = load_settings()


@overload
def _get_setting(key: str, default: str) -> str: ...


@overload
def _get_setting(key: str, default: None = None) -> str | None: ...


def _get_setting(key: str, default: str | None = None) -> str | None:
    """Return a configuration value from settings.yaml overriding environment variables.

    Empty strings in either source are treated as missing values so the
    provided ``default`` is used instead. This prevents downstream code from
    receiving empty strings when it expects ``None`` or a usable value.
    """
    value = _SETTINGS.get(key)
    if value in (None, ""):
        # Avoid leaking developer .env values into the test suite
        if os.environ.get("PYTEST_CURRENT_TEST") and key in {
            "WORDNIK_API_KEY",
            "OPENAI_API_KEY",
            "IMMICH_API_KEY",
            "JELLYFIN_API_KEY",
            "IMMICH_TIME_BUFFER",
        }:
            value = default
        else:
            value = os.getenv(key, default)
    if value == "":
        return default
    return value


# Derive the application directory from this file location.  This allows the
# code to run from arbitrary paths without requiring users to set ``APP_DIR``
# manually.  An environment variable can still override the value for advanced
# scenarios such as tests or non-standard deployments.
DEFAULT_APP_DIR = Path(__file__).resolve().parent.parent
# Allow overriding important paths via environment variables for easier testing
# and deployment in restricted environments.
APP_DIR = Path(_get_setting("APP_DIR", str(DEFAULT_APP_DIR)))
DATA_DIR = Path(_get_setting("DATA_DIR", "/journals"))
PROMPTS_FILE = Path(_get_setting("PROMPTS_FILE", str(APP_DIR / "prompts.yaml")))
STATIC_DIR = Path(_get_setting("STATIC_DIR", str(APP_DIR / "static")))
TEMPLATES_DIR = Path(_get_setting("TEMPLATES_DIR", str(APP_DIR / "templates")))
_MINDLOOM_LOG_PATH = _get_setting(
    "MINDLOOM_ENERGY_LOG_PATH",
    "/home/eoghann/docker/mindloom/data/energy_log.yaml",
)
MINDLOOM_ENERGY_LOG_PATH = (
    Path(_MINDLOOM_LOG_PATH) if _MINDLOOM_LOG_PATH is not None else None
)
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

# AudioBookShelf configuration
AUDIOBOOKSHELF_URL = _get_setting("AUDIOBOOKSHELF_URL")
AUDIOBOOKSHELF_API_TOKEN = _get_setting("AUDIOBOOKSHELF_API_TOKEN")
AUDIOBOOKSHELF_POLL_ENABLED = (
    _get_setting("AUDIOBOOKSHELF_POLL_ENABLED", "false").lower() == "true"
)
AUDIOBOOKSHELF_POLL_INTERVAL_SECONDS = int(
    _get_setting("AUDIOBOOKSHELF_POLL_INTERVAL_SECONDS", "600")
)

# LocationIQ reverse geocoding configuration
LOCATIONIQ_API_KEY = _get_setting("LOCATIONIQ_API_KEY")

# Disk cache configuration for reverse geocoding
_DEFAULT_CACHE_PATH = (
    Path(_get_setting("DATA_DIR", "/journals")) / ".cache" / "reverse_geocode.json"
)
GEO_CACHE_PATH = Path(_get_setting("GEO_CACHE_PATH", str(_DEFAULT_CACHE_PATH)))
GEO_CACHE_TTL_SECONDS = int(_get_setting("GEO_CACHE_TTL_SECONDS", "86400"))
GEO_CACHE_MAX_ENTRIES = int(_get_setting("GEO_CACHE_MAX_ENTRIES", "1000"))

# Number of retry attempts for Numbers API requests.
NUMBERS_API_RETRIES = int(_get_setting("NUMBERS_API_RETRIES", "0"))

# File logging path - defaults to ``DATA_DIR/.logs/echo_journal.log`` but can
# be overridden via the ``LOG_FILE`` environment variable.
LOG_FILE = Path(_get_setting("LOG_FILE", str(DATA_DIR / ".logs" / "echo_journal.log")))

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
