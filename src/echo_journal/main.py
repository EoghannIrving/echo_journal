"""Echo Journal FastAPI application."""

# pylint: disable=import-error,too-many-lines,global-statement

import asyncio
import base64
import binascii
import hmac
import json
import logging
import os
import re
import secrets
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import DefaultDict, Dict
from urllib.parse import urlparse

import aiofiles
import bleach
import httpx
import markdown
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.routing import Mount

from . import config
from .ai_prompt_utils import fetch_ai_prompt
from .file_utils import (
    format_weather,
    load_json_file,
    parse_entry,
    parse_frontmatter,
    read_existing_frontmatter,
    safe_entry_path,
    split_frontmatter,
    weather_description,
)
from .immich_utils import update_photo_metadata
from .jellyfin_utils import update_media_metadata, update_song_metadata
from .numbers_utils import fetch_date_fact
from .prompt_utils import _choose_anchor, generate_prompt, load_prompts
from .settings_utils import SETTINGS_PATH, load_settings, save_settings
from .weather_utils import build_frontmatter, time_of_day_label

# Provide pathlib.Path.is_relative_to on Python < 3.9
if not hasattr(Path, "is_relative_to"):

    def _is_relative_to(self: Path, *other: Path) -> bool:
        try:
            self.relative_to(*other)
            return True
        except ValueError:
            return False

    setattr(Path, "is_relative_to", _is_relative_to)

app = FastAPI()

# Aliases for configuration values to maintain compatibility for external imports
DATA_DIR = config.DATA_DIR
PROMPTS_FILE = config.PROMPTS_FILE
IMMICH_URL = config.IMMICH_URL
IMMICH_API_KEY = config.IMMICH_API_KEY
NOMINATIM_USER_AGENT = config.NOMINATIM_USER_AGENT
IMMICH_ALLOWED_HOSTS = {"immich", "localhost"}

AUTH_ENABLED = False
logger: logging.Logger
jellyfin_logger: logging.Logger
auth_logger: logging.Logger
ai_logger: logging.Logger
immich_logger: logging.Logger
fact_logger: logging.Logger
templates: Jinja2Templates | None


def _refresh_config_vars() -> None:
    """Refresh module-level aliases to configuration values."""
    global DATA_DIR, PROMPTS_FILE, IMMICH_URL, IMMICH_API_KEY, NOMINATIM_USER_AGENT, IMMICH_ALLOWED_HOSTS
    DATA_DIR = config.DATA_DIR
    PROMPTS_FILE = config.PROMPTS_FILE
    IMMICH_URL = config.IMMICH_URL
    IMMICH_API_KEY = config.IMMICH_API_KEY
    NOMINATIM_USER_AGENT = config.NOMINATIM_USER_AGENT

    # Restrict Immich asset proxying to known hosts derived from configuration.
    IMMICH_ALLOWED_HOSTS = {"immich", "localhost"}
    if IMMICH_URL:
        try:
            host = urlparse(IMMICH_URL).hostname
        except ValueError:
            host = None
        if host:
            IMMICH_ALLOWED_HOSTS.add(host)


def _configure_auth() -> None:
    """Determine whether Basic Auth should be enforced."""
    global AUTH_ENABLED
    AUTH_ENABLED = False
    if config.BASIC_AUTH_USERNAME and config.BASIC_AUTH_PASSWORD:
        AUTH_ENABLED = True
    elif config.BASIC_AUTH_USERNAME or config.BASIC_AUTH_PASSWORD:
        logging.warning(
            "Both BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD must be set; disabling auth"
        )


def _configure_logging() -> None:
    """Configure application logging handlers and loggers."""
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                config.LOG_FILE,
                encoding="utf-8",
                maxBytes=config.LOG_MAX_BYTES,
                backupCount=config.LOG_BACKUP_COUNT,
            )
        )
    except OSError:
        pass

    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.DEBUG),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )
    global logger, jellyfin_logger, auth_logger, ai_logger, immich_logger, fact_logger
    logger = logging.getLogger("ej.timing")
    jellyfin_logger = logging.getLogger("ej.jellyfin")
    auth_logger = logging.getLogger("ej.auth")
    ai_logger = logging.getLogger("ej.ai_prompt")
    immich_logger = logging.getLogger("ej.immich")
    fact_logger = logging.getLogger("ej.fact")


def _configure_mounts_and_templates() -> None:
    """Mount static files and initialize templates using current settings."""
    global templates
    for route in list(app.routes):
        if isinstance(route, Mount) and route.path == "/static":
            app.routes.remove(route)
    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
    try:
        templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))
    except AssertionError:
        logging.getLogger(__name__).warning(
            "Jinja2 is not installed; template rendering is disabled"
        )

        class _MissingTemplates:  # pragma: no cover - simple runtime guard
            def TemplateResponse(self, *_args, **_kwargs) -> HTMLResponse:  # type: ignore[override]
                raise RuntimeError("Jinja2 must be installed to render templates")

        templates = _MissingTemplates()  # type: ignore[assignment]


def reload_from_config() -> None:
    """Reinitialize globals derived from configuration values."""
    _refresh_config_vars()
    _configure_auth()
    _configure_logging()
    _configure_mounts_and_templates()


# Initialize components on module import
reload_from_config()

# Keys configurable via environment variables and editable from the settings page.
# Values provided in ``settings.yaml`` override these defaults.
NON_EDITABLE_SETTING_KEYS = {"APP_DIR", "STATIC_DIR", "TEMPLATES_DIR"}

ENV_SETTING_KEYS = [
    "DATA_DIR",
    "PROMPTS_FILE",
    "WORDNIK_API_KEY",
    "OPENAI_API_KEY",
    "IMMICH_URL",
    "IMMICH_API_KEY",
    "IMMICH_TIME_BUFFER",
    "JELLYFIN_URL",
    "JELLYFIN_API_KEY",
    "JELLYFIN_USER_ID",
    "JELLYFIN_PAGE_SIZE",
    "JELLYFIN_PLAY_THRESHOLD",
    "NOMINATIM_USER_AGENT",
    "LOG_LEVEL",
    "LOG_FILE",
    "LOG_MAX_BYTES",
    "LOG_BACKUP_COUNT",
    "BASIC_AUTH_USERNAME",
    "BASIC_AUTH_PASSWORD",
]

# Store recent request timings on the FastAPI state
MAX_TIMINGS = 50
app.state.request_timings = []

# Locks for concurrent saves keyed by entry path
SAVE_LOCKS: DefaultDict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

ASSET_ID_RE = re.compile(r"^[a-fA-F0-9-]+$")


def _validate_proxy_params(asset_id: str, base_url: str) -> None:
    """Validate asset ID and Immich base URL before proxying requests."""
    if not ASSET_ID_RE.fullmatch(asset_id):
        immich_logger.warning("Invalid asset id requested: %s", asset_id)
        raise HTTPException(status_code=400, detail="Invalid asset ID")
    try:
        host = urlparse(base_url).hostname
    except ValueError:
        host = None
    if not host or host not in IMMICH_ALLOWED_HOSTS:
        immich_logger.warning("Blocked Immich host: %s", base_url)
        raise HTTPException(status_code=400, detail="Invalid Immich host")


def _needs_initial_setup() -> bool:
    """Return True when essential paths or settings are missing."""
    for path in (config.DATA_DIR, config.PROMPTS_FILE, SETTINGS_PATH):
        if not path.exists():
            return True
    return False


@app.middleware("http")
async def basic_auth_middleware(request: Request, call_next):
    """Enforce optional HTTP Basic authentication."""
    if AUTH_ENABLED:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})
        try:
            encoded = auth_header.split(" ", 1)[1]
            decoded = base64.b64decode(encoded).decode("utf-8")
            username, password = decoded.split(":", 1)
        except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
            auth_logger.warning("Invalid Basic auth header: %s", exc)
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})
        if not (
            hmac.compare_digest(username, config.BASIC_AUTH_USERNAME or "")
            and hmac.compare_digest(password, config.BASIC_AUTH_PASSWORD or "")
        ):
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})
    return await call_next(request)


CSRF_COOKIE_NAME = "csrftoken"


@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    """Simple CSRF protection using a cookie + header token."""
    token = request.cookies.get(CSRF_COOKIE_NAME)
    if not token:
        token = secrets.token_urlsafe(32)
    request.state.csrf_token = token
    if request.method not in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        header_token = request.headers.get("X-CSRF-Token")
        if not header_token or not hmac.compare_digest(token, header_token):
            return JSONResponse(
                status_code=403, content={"detail": "Invalid CSRF token"}
            )
    response = await call_next(request)
    response.set_cookie(CSRF_COOKIE_NAME, token, httponly=True, samesite="lax")
    return response


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    """Record processing time for each request and attach header."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Response-Time"] = f"{elapsed:.3f}s"

    timings = app.state.request_timings
    timings.append({"path": request.url.path, "time": elapsed})
    if len(timings) > MAX_TIMINGS:
        timings.pop(0)

    logger.info("%s completed in %.3fs", request.url.path, elapsed)
    return response


@app.get("/")
async def index(request: Request):  # pylint: disable=too-many-locals
    """Render the journal entry page for the current day."""
    if _needs_initial_setup():
        return RedirectResponse(url="/settings", status_code=307)
    today = date.today()
    date_str = today.isoformat()
    file_path = safe_entry_path(date_str, config.DATA_DIR)

    if file_path.exists():
        try:
            async with aiofiles.open(file_path, "r", encoding=config.ENCODING) as fh:
                md_content = await fh.read()
        except OSError as exc:
            raise HTTPException(status_code=500, detail="Could not read entry") from exc
        frontmatter, body = split_frontmatter(md_content)
        meta = parse_frontmatter(frontmatter) if frontmatter else {}
        prompt, entry = parse_entry(body)
        if not prompt and not entry:
            entry = body.strip()
        category = meta.get("category", "")
        anchor = meta.get("anchor", "")
        wotd = meta.get("wotd", "")
        wotd_def = meta.get("wotd_def", "")
        mood = meta.get("mood", "")
        energy = meta.get("energy", "")
    else:
        prompt = ""
        category = ""
        anchor = ""
        entry = ""
        wotd = ""
        wotd_def = ""
        mood = ""
        energy = ""

    gap = _days_since_last_entry(config.DATA_DIR, today)
    missing_yesterday = gap is None or gap > 1

    settings = load_settings()
    integrations = {
        "wordnik": settings.get("INTEGRATION_WORDNIK", "true").lower() != "false",
        "immich": settings.get("INTEGRATION_IMMICH", "true").lower() != "false",
        "jellyfin": settings.get("INTEGRATION_JELLYFIN", "true").lower() != "false",
        "fact": settings.get("INTEGRATION_FACT", "true").lower() != "false",
    }
    integrations["ai"] = bool(config.OPENAI_API_KEY)
    if templates is None:
        raise RuntimeError("Templates not configured")

    return templates.TemplateResponse(
        request,
        "echo_journal.html",
        {
            "request": request,
            "prompt": prompt,
            "category": category,
            "anchor": anchor,
            "date": date_str,
            "content": entry,
            "readonly": False,  # Explicit
            "active_page": "home",
            "wotd": wotd,
            "wotd_def": wotd_def,
            "mood": mood,
            "energy": energy,
            "missing_yesterday": missing_yesterday,
            "integrations": integrations,
            "csrf_token": request.state.csrf_token,
        },
    )


def _days_since_last_entry(
    data_dir: Path | None = None, today: date | None = None
) -> int | None:
    """Return days since the most recent entry prior to ``today``."""
    data_dir = data_dir or config.DATA_DIR
    today = today or date.today()
    last_entry: date | None = None
    for file in data_dir.glob("*.md"):
        try:
            entry_date = datetime.strptime(file.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if entry_date >= today:
            continue
        if last_entry is None or entry_date > last_entry:
            last_entry = entry_date
    if last_entry is None:
        return None
    return (today - last_entry).days


def _with_updated_save_time(frontmatter: str | None, label: str) -> str | None:
    """Return frontmatter with the ``save_time`` value inserted or replaced."""
    if not frontmatter:
        return f"save_time: {label}"
    lines = frontmatter.splitlines()
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("save_time:"):
            indent = line[: len(line) - len(stripped)]
            lines[i] = f"{indent}save_time: {label}"
            break
    else:
        lines.append(f"save_time: {label}")
    return "\n".join(lines)


def _with_updated_category(frontmatter: str | None, category: str | None) -> str | None:
    """Return frontmatter with the ``category`` value inserted or replaced."""
    if category is None or category == "":
        return frontmatter
    if not frontmatter:
        return f"category: {category}"
    lines = frontmatter.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("category:"):
            lines[i] = f"category: {category}"
            break
    else:
        lines.append(f"category: {category}")
    return "\n".join(lines)


def _update_field(frontmatter: str | None, key: str, value) -> str | None:
    """Generic helper to update or insert a frontmatter field."""
    if value is None or value == "" or value == []:
        return frontmatter
    try:
        # ``yaml.safe_dump`` ensures values with special characters are quoted
        # properly for YAML frontmatter.
        value_str = (
            yaml.safe_dump(value, default_flow_style=True, explicit_end=False)
            .strip()
            .splitlines()[0]
        )
    except yaml.YAMLError:
        value_str = str(value)
    if not frontmatter:
        return f"{key}: {value_str}"
    lines = frontmatter.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            lines[i] = f"{key}: {value_str}"
            break
    else:
        lines.append(f"{key}: {value_str}")
    return "\n".join(lines)


def _with_updated_mood(frontmatter: str | None, mood: str | None) -> str | None:
    return _update_field(frontmatter, "mood", mood)


def _with_updated_energy(frontmatter: str | None, energy: str | None) -> str | None:
    return _update_field(frontmatter, "energy", energy)


@app.post("/entry")
async def save_entry(data: dict):  # pylint: disable=too-many-locals
    """Save a journal entry for the provided date."""
    entry_date = data.get("date")
    content = data.get("content")
    prompt = data.get("prompt")
    category = (
        bleach.clean(data.get("category") or "")
        .replace("\n", " ")
        .replace("\r", " ")
        .strip()
        or None
    )
    location = data.get("location") or {}
    weather = data.get("weather")
    mood = bleach.clean(data.get("mood") or "").strip() or None
    energy = bleach.clean(data.get("energy") or "").strip() or None
    integrations = data.get("integrations") or {}

    if not entry_date or not content or not prompt:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing fields"},
        )

    # Ensure DATA_DIR exists before attempting to save
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        file_path = safe_entry_path(entry_date, config.DATA_DIR)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Invalid date"},
        )
    first_save = not file_path.exists()
    if first_save:
        frontmatter: str | None = await build_frontmatter(
            location, weather, integrations
        )
    else:
        frontmatter = await read_existing_frontmatter(file_path)

    # Update or add save_time field
    label = time_of_day_label()
    frontmatter = _with_updated_save_time(frontmatter, label)
    frontmatter = _with_updated_category(frontmatter, category)
    frontmatter = _with_updated_mood(frontmatter, mood)
    frontmatter = _with_updated_energy(frontmatter, energy)
    try:
        fact_date = datetime.strptime(entry_date, "%Y-%m-%d").date()
    except ValueError:
        fact_date = None
    if fact_date and integrations.get("fact", True):
        retries = config.NUMBERS_API_RETRIES
        fact = None
        for _ in range(retries + 1):
            fact = await fetch_date_fact(fact_date)
            if fact:
                break
        if fact is None:
            fact_logger.warning("No fact found for %s", fact_date)
        frontmatter = _update_field(frontmatter, "fact", fact)

    md_body = f"# Prompt\n{prompt}\n\n# Entry\n{content}"
    if frontmatter is not None:
        md_text = f"---\n{frontmatter}\n---\n{md_body}"
    else:
        md_text = md_body

    lock = SAVE_LOCKS[str(file_path)]
    async with lock:
        async with aiofiles.open(file_path, "w", encoding=config.ENCODING) as fh:
            await fh.write(md_text)

    if integrations.get("immich", True):
        await update_photo_metadata(entry_date, file_path)
    if integrations.get("jellyfin", True):
        await update_song_metadata(entry_date, file_path)
        await update_media_metadata(entry_date, file_path)

    return {"status": "success"}


async def _load_extra_meta(
    md_file: Path, meta: dict
) -> None:  # pylint: disable=too-many-branches
    """Populate ``meta`` with photo, song and media info if present."""
    meta_dir = md_file.parent / ".meta"
    if meta.get("photos") in (None, [], "[]"):
        json_path = meta_dir / f"{md_file.stem}.photos.json"
        if json_path.exists():
            try:
                async with aiofiles.open(
                    json_path, "r", encoding=config.ENCODING
                ) as jh:
                    photos_text = await jh.read()
                if json.loads(photos_text):
                    meta["photos"] = "1"
            except (OSError, ValueError):
                pass
    if not meta.get("songs"):
        songs_path = meta_dir / f"{md_file.stem}.songs.json"
        if songs_path.exists():
            try:
                async with aiofiles.open(
                    songs_path, "r", encoding=config.ENCODING
                ) as sh:
                    songs_text = await sh.read()
                songs_data = json.loads(songs_text)
                if songs_data:
                    if isinstance(songs_data, list) and isinstance(songs_data[0], dict):
                        meta["songs"] = songs_data[0].get("track") or "1"
                    else:
                        meta["songs"] = "1"
            except (OSError, ValueError):
                pass
    if not meta.get("media"):
        media_path = meta_dir / f"{md_file.stem}.media.json"
        if media_path.exists():
            try:
                async with aiofiles.open(
                    media_path, "r", encoding=config.ENCODING
                ) as mh:
                    media_text = await mh.read()
                media_data = json.loads(media_text)
                if media_data:
                    meta["media"] = "1"
            except (OSError, ValueError):
                pass


async def _collect_entries() -> list[dict]:
    """Return a list of entries found under ``DATA_DIR``."""
    entries: list[dict] = []
    for file in config.DATA_DIR.rglob("*.md"):
        name = file.stem
        try:
            entry_date = datetime.strptime(name, "%Y-%m-%d").date()
        except ValueError:
            entry_date = None
        try:
            async with aiofiles.open(file, "r", encoding=config.ENCODING) as fh:
                content = await fh.read(8192)
        except OSError:
            continue
        frontmatter, body = split_frontmatter(content)
        meta = parse_frontmatter(frontmatter) if frontmatter else {}
        await _load_extra_meta(file, meta)
        prompt, _ = parse_entry(body)
        entries.append(
            {"date": entry_date, "name": name, "prompt": prompt, "meta": meta}
        )
    return entries


@app.get("/archive", response_class=HTMLResponse)
async def archive_view(  # pylint: disable=too-many-branches
    request: Request,
    sort_by: str | None = None,
    filter_: str | None = Query(None, alias="filter"),
):
    """Render an archive of all journal entries grouped by month."""

    sort_by = sort_by or "date"

    all_entries = await _collect_entries()

    if filter_ == "has_location":
        all_entries = [e for e in all_entries if e["meta"].get("location")]
    elif filter_ == "has_weather":
        all_entries = [e for e in all_entries if e["meta"].get("weather")]
    elif filter_ == "has_photos":
        all_entries = [
            e for e in all_entries if e["meta"].get("photos") not in (None, "[]", [])
        ]
    elif filter_ == "has_songs":
        all_entries = [e for e in all_entries if e["meta"].get("songs")]
    elif filter_ == "has_media":
        all_entries = [e for e in all_entries if e["meta"].get("media")]

    def _sort_key(e: dict) -> date:
        return e["date"] or date.min

    if sort_by == "date":
        all_entries.sort(key=_sort_key, reverse=True)
    elif sort_by in {"location", "weather", "photos", "songs", "media"}:
        all_entries.sort(key=lambda e: e["meta"].get(sort_by) or "")
    else:
        # default to date sorting if unrecognised
        sort_by = "date"
        all_entries.sort(key=_sort_key, reverse=True)

    entries_by_month: dict[str, list[tuple[str, str, dict]]] = defaultdict(list)
    for entry in all_entries:
        if entry["date"]:
            month_key = entry["date"].strftime("%Y-%m")
            date_str = entry["date"].isoformat()
        else:
            month_key = "Unknown"
            date_str = entry["name"]
        entries_by_month[month_key].append((date_str, entry["prompt"], entry["meta"]))

    # Sort months descending (latest first)
    sorted_entries = dict(sorted(entries_by_month.items(), reverse=True))
    if sorted_entries:
        current_month = next(iter(sorted_entries))
    else:
        current_month = datetime.now().strftime("%Y-%m")

    if templates is None:
        raise RuntimeError("Templates not configured")

    return templates.TemplateResponse(
        request,
        "archives.html",
        {
            "request": request,
            "entries": sorted_entries,
            "active_page": "archive",
            "sort_by": sort_by,
            "filter_val": filter_,
            "current_month": current_month,
        },
    )


@app.get("/archive/{entry_date}")
async def archive_entry(request: Request, entry_date: str):
    """Display a previously written journal entry."""
    try:
        file_path = safe_entry_path(entry_date, config.DATA_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Entry not found") from exc
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Entry not found")

    await update_photo_metadata(entry_date, file_path)

    try:
        async with aiofiles.open(file_path, "r", encoding=config.ENCODING) as fh:
            frontmatter, body = split_frontmatter(await fh.read())
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Could not read entry") from exc

    meta = parse_frontmatter(frontmatter) if frontmatter else {}

    prompt, entry = parse_entry(body)
    if not prompt and not entry:
        entry = body.strip()

    meta_dir = file_path.parent / ".meta"
    photos = await load_json_file(meta_dir / f"{file_path.stem}.photos.json")

    songs = await load_json_file(meta_dir / f"{file_path.stem}.songs.json")

    media = await load_json_file(meta_dir / f"{file_path.stem}.media.json")
    if templates is None:
        raise RuntimeError("Templates not configured")

    return templates.TemplateResponse(
        request,
        "archive-entry.html",
        {
            "request": request,
            "content": entry,
            "content_html": bleach.clean(
                markdown.markdown(entry),
                tags=bleach.sanitizer.ALLOWED_TAGS.union({"p", "pre"}),
                attributes=bleach.sanitizer.ALLOWED_ATTRIBUTES,
            ),
            "date": entry_date,
            "prompt": prompt,
            "location": meta.get("location", ""),
            "weather": format_weather(meta["weather"]) if meta.get("weather") else "",
            "weather_desc": (
                weather_description(meta["weather"]) if meta.get("weather") else ""
            ),
            "mood": meta.get("mood", ""),
            "energy": meta.get("energy", ""),
            "wotd": meta.get("wotd", ""),
            "wotd_def": meta.get("wotd_def", ""),
            "photos": photos,
            "songs": songs,
            "media": media,
            "fact": meta.get("fact", ""),
            "meta": meta,
            "readonly": True,  # Read-only mode for archive
            "active_page": "archive",
        },
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Render the user settings page."""
    if templates is None:
        raise RuntimeError("Templates not configured")

    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "request": request,
            "active_page": "settings",
            "csrf_token": request.state.csrf_token,
        },
    )


@app.get("/metrics")
async def metrics() -> JSONResponse:
    """Return recent request timing information."""
    return JSONResponse(content={"timings": app.state.request_timings})


async def _gather_entry_stats() -> tuple[dict, int, int, list[date]]:
    """Return aggregated entry counts, total words and entry dates."""
    counts: dict[str, DefaultDict[str, int]] = {
        "week": defaultdict(int),
        "month": defaultdict(int),
        "year": defaultdict(int),
    }
    total_words = 0
    total_entries = 0
    entry_dates: list[date] = []

    for file in config.DATA_DIR.rglob("*.md"):
        try:
            entry_date = datetime.strptime(file.stem, "%Y-%m-%d").date()
        except ValueError:
            continue

        entry_dates.append(entry_date)

        try:
            async with aiofiles.open(file, "r", encoding=config.ENCODING) as fh:
                content = await fh.read()
        except OSError:
            continue

        body = split_frontmatter(content)[1]
        entry_text = parse_entry(body)[1] or body.strip()

        iso = entry_date.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        month_key = entry_date.strftime("%Y-%m")
        year_key = entry_date.strftime("%Y")

        counts["week"][week_key] += 1
        counts["month"][month_key] += 1
        counts["year"][year_key] += 1
        total_words += len(entry_text.split())
        total_entries += 1

    return counts, total_words, total_entries, entry_dates


def _calculate_streaks(entry_dates: list[date]) -> dict[str, int]:
    """Return current and longest day/week streaks."""
    unique_dates = sorted(set(entry_dates))
    current_day_streak = 0
    longest_day_streak = 0
    prev = None
    for d in unique_dates:
        if prev and d == prev + timedelta(days=1):
            current_day_streak += 1
        else:
            current_day_streak = 1 if unique_dates else 0
        longest_day_streak = max(longest_day_streak, current_day_streak)
        prev = d

    if not unique_dates:
        current_day_streak = longest_day_streak = 0

    week_starts = sorted(
        {
            date.fromisocalendar(d.isocalendar()[0], d.isocalendar()[1], 1)
            for d in unique_dates
        }
    )
    current_week_streak = 0
    longest_week_streak = 0
    prev_week = None
    for w in week_starts:
        if prev_week and (w - prev_week).days == 7:
            current_week_streak += 1
        else:
            current_week_streak = 1 if week_starts else 0
        longest_week_streak = max(longest_week_streak, current_week_streak)
        prev_week = w

    if not week_starts:
        current_week_streak = longest_week_streak = 0

    return {
        "current_day_streak": current_day_streak,
        "longest_day_streak": longest_day_streak,
        "current_week_streak": current_week_streak,
        "longest_week_streak": longest_week_streak,
    }


@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    """Render journal statistics including entry counts and words."""
    counts, total_words, total_entries, dates = await _gather_entry_stats()
    streaks = _calculate_streaks(dates)

    stats: Dict[str, object] = {
        "weeks": sorted(counts["week"].items(), reverse=True),
        "months": sorted(counts["month"].items(), reverse=True),
        "years": sorted(counts["year"].items(), reverse=True),
        "total_entries": total_entries,
        "total_words": total_words,
        "average_words": round(total_words / total_entries, 1) if total_entries else 0,
        **streaks,
    }
    if templates is None:
        raise RuntimeError("Templates not configured")

    return templates.TemplateResponse(
        "stats.html",
        {"request": request, "stats": stats, "active_page": "stats"},
    )


@app.get("/api/ai_prompt")
async def ai_prompt(mood: str | None = None, energy: int | None = None) -> dict:
    """Return a prompt generated by an external AI service."""
    ai_logger.debug("AI prompt requested: mood=%s energy=%s", mood, energy)
    # ``fetch_ai_prompt`` requires an anchor. If mood/energy are missing,
    # ``_choose_anchor`` returns ``None`` which previously resulted in a 503
    # error for users who hadn't selected mood or energy. Default to a
    # gentle "soft" anchor so the endpoint remains usable without prior
    # selections.
    anchor = _choose_anchor(mood, energy) or "soft"
    ai_logger.debug("Using anchor '%s'", anchor)
    result = await fetch_ai_prompt(anchor)
    if not result:
        ai_logger.error("AI prompt fetch failed for anchor '%s'", anchor)
        raise HTTPException(status_code=503, detail="AI prompt unavailable")

    prompts = await load_prompts()
    prompts.append(result)
    async with aiofiles.open(config.PROMPTS_FILE, "w", encoding=config.ENCODING) as fh:
        dump_text = yaml.safe_dump(prompts, allow_unicode=True, sort_keys=False)
        await fh.write(dump_text)
    ai_logger.info("Received AI prompt id=%s", result.get("id"))
    return {
        "prompt": result.get("prompt", ""),
        "anchor": result.get("anchor", ""),
        "tags": result.get("tags", []),
        "id": result.get("id", ""),
    }


@app.get("/api/new_prompt")
async def new_prompt(
    mood: str | None = None,
    energy: int | None = None,
    debug: bool = False,
) -> dict:
    """Return a freshly generated journal prompt."""
    return await generate_prompt(mood=mood, energy=energy, debug=debug)


@app.get("/api/reverse_geocode")
async def reverse_geocode(lat: float, lon: float):
    """Return location details for given coordinates using Nominatim."""
    url = "https://nominatim.openstreetmap.org/reverse"
    params: dict[str, float | int | str] = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 18,
    }
    headers = {"User-Agent": config.NOMINATIM_USER_AGENT or ""}

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Reverse geocoding failed") from exc

    return {
        "display_name": data.get("display_name"),
        "city": data.get("address", {}).get("city")
        or data.get("address", {}).get("town")
        or data.get("address", {}).get("village"),
        "region": data.get("address", {}).get("state"),
        "country": data.get("address", {}).get("country"),
    }


@app.get("/api/thumbnail/{asset_id}")
async def proxy_thumbnail(asset_id: str, size: str = "thumbnail"):
    """Fetch an asset thumbnail from Immich using the API key."""
    if not config.IMMICH_URL:
        raise HTTPException(status_code=404, detail="Immich not configured")
    _validate_proxy_params(asset_id, config.IMMICH_URL)
    headers = {"x-api-key": config.IMMICH_API_KEY} if config.IMMICH_API_KEY else {}
    url = f"{config.IMMICH_URL}/assets/{asset_id}/thumbnail?size={size}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code, detail="Thumbnail fetch failed"
        )
    content_type = resp.headers.get("content-type", "image/jpeg")
    return Response(content=resp.content, media_type=content_type)


@app.get("/api/asset/{asset_id}")
async def proxy_asset(asset_id: str):
    """Fetch a full-size asset from Immich using the API key."""
    if not config.IMMICH_URL:
        raise HTTPException(status_code=404, detail="Immich not configured")
    _validate_proxy_params(asset_id, config.IMMICH_URL)
    headers = {"x-api-key": config.IMMICH_API_KEY} if config.IMMICH_API_KEY else {}
    url = f"{config.IMMICH_URL}/assets/{asset_id}/original"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Asset fetch failed")
    content_type = resp.headers.get("content-type", "application/octet-stream")
    return Response(content=resp.content, media_type=content_type)


@app.get("/api/settings")
async def get_settings() -> Dict[str, str]:
    """Return configuration values from the environment and ``settings.yaml``."""

    values: Dict[str, str] = {}
    for key in ENV_SETTING_KEYS:
        value = getattr(config, key, os.getenv(key, ""))
        if value is None:
            value = ""
        elif not isinstance(value, str):
            value = str(value)
        values[key] = value

    # Include any additional keys from settings.yaml that aren't in
    # ``ENV_SETTING_KEYS``.
    for key, val in load_settings().items():
        if key in NON_EDITABLE_SETTING_KEYS:
            continue
        values.setdefault(key, val)

    return values


@app.post("/api/settings")
async def update_settings(values: Dict[str, str]) -> Dict[str, str]:
    """Merge provided values into ``settings.yaml`` and return the updated mapping."""
    for key in NON_EDITABLE_SETTING_KEYS:
        values.pop(key, None)
    return save_settings(values)


@app.post("/api/backfill_songs")
async def backfill_jellyfin_metadata() -> dict:
    """Generate missing songs.json and media.json files for existing entries."""
    jellyfin_logger.info("Starting Jellyfin metadata backfill")
    songs_added = 0
    media_added = 0
    for md_file in config.DATA_DIR.rglob("*.md"):
        meta_dir = md_file.parent / ".meta"
        songs_path = meta_dir / f"{md_file.stem}.songs.json"
        media_path = meta_dir / f"{md_file.stem}.media.json"
        if songs_path.exists() and media_path.exists():
            jellyfin_logger.debug("%s already has songs and media metadata", md_file)
            continue
        try:
            datetime.strptime(md_file.stem, "%Y-%m-%d")
        except ValueError:
            jellyfin_logger.debug("Skipping non-entry file %s", md_file)
            continue
        if not songs_path.exists():
            jellyfin_logger.info("Backfilling songs for %s", md_file.stem)
            await update_song_metadata(md_file.stem, md_file)
            if songs_path.exists():
                songs_added += 1
        if not media_path.exists():
            jellyfin_logger.info("Backfilling media for %s", md_file.stem)
            await update_media_metadata(md_file.stem, md_file)
            if media_path.exists():
                media_added += 1
    jellyfin_logger.info(
        "Backfill complete; added %d song files and %d media files",
        songs_added,
        media_added,
    )
    return {"songs_added": songs_added, "media_added": media_added}


def main() -> None:
    """Run the Echo Journal ASGI application.

    Host, port, and optional TLS settings can be overridden via the
    ``ECHO_JOURNAL_HOST``, ``ECHO_JOURNAL_PORT``, ``ECHO_JOURNAL_SSL_KEYFILE``,
    and ``ECHO_JOURNAL_SSL_CERTFILE`` environment variables. By default the
    server binds to ``127.0.0.1:8000`` which is suitable when running behind a
    reverse proxy that terminates TLS.
    """

    host = os.getenv("ECHO_JOURNAL_HOST", "127.0.0.1")
    port = int(os.getenv("ECHO_JOURNAL_PORT", "8000"))
    ssl_keyfile = os.getenv("ECHO_JOURNAL_SSL_KEYFILE")
    ssl_certfile = os.getenv("ECHO_JOURNAL_SSL_CERTFILE")

    uvicorn.run(
        "echo_journal.main:app",
        host=host,
        port=port,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
    )


if __name__ == "__main__":
    main()
