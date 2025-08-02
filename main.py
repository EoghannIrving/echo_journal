"""Echo Journal FastAPI application."""

# pylint: disable=import-error

import asyncio
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from typing import Dict

import json
import logging
from logging.handlers import RotatingFileHandler
import time

import aiofiles
import bleach
import httpx
import markdown
import base64
import hmac
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import (
    DATA_DIR,
    STATIC_DIR,
    TEMPLATES_DIR,
    ENCODING,
    IMMICH_URL,
    IMMICH_API_KEY,
    LOG_FILE,
    LOG_LEVEL,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
    BASIC_AUTH_USERNAME,
    BASIC_AUTH_PASSWORD,
)
from file_utils import (
    safe_entry_path,
    parse_entry,
    read_existing_frontmatter,
    split_frontmatter,
    parse_frontmatter,
    format_weather,
    load_json_file,
)
from immich_utils import update_photo_metadata
from jellyfin_utils import update_song_metadata, update_media_metadata
from prompt_utils import generate_prompt
from weather_utils import build_frontmatter, time_of_day_label
from activation_engine_utils import fetch_tags


# Provide pathlib.Path.is_relative_to on Python < 3.9
if not hasattr(Path, "is_relative_to"):

    def _is_relative_to(self: Path, *other: Path) -> bool:
        try:
            self.relative_to(*other)
            return True
        except ValueError:
            return False

    Path.is_relative_to = _is_relative_to  # type: ignore[attr-defined]

app = FastAPI()

# Determine whether Basic Auth should be enforced.
AUTH_ENABLED = False
if BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD:
    AUTH_ENABLED = True
elif BASIC_AUTH_USERNAME or BASIC_AUTH_PASSWORD:
    logging.warning(
        "Both BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD must be set; disabling auth"
    )


# Setup logging to both the console and a rotating file under ``DATA_DIR``
handlers = [logging.StreamHandler()]
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    handlers.append(
        RotatingFileHandler(
            LOG_FILE,
            encoding="utf-8",
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
        )
    )
except OSError:
    # Fall back to console-only logging if file creation fails
    pass

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=handlers,
)
logger = logging.getLogger("ej.timing")
songs_logger = logging.getLogger("ej.jellyfin")

# Store recent request timings on the FastAPI state
MAX_TIMINGS = 50
app.state.request_timings = []

# Locks for concurrent saves keyed by entry path
SAVE_LOCKS = defaultdict(asyncio.Lock)

# Mount all static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


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
        except Exception:  # pylint: disable=broad-except
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})
        if not (
            hmac.compare_digest(username, BASIC_AUTH_USERNAME)
            and hmac.compare_digest(password, BASIC_AUTH_PASSWORD)
        ):
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})
    return await call_next(request)


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
async def index(request: Request):
    """Render the journal entry page for the current day."""
    today = date.today()
    date_str = today.isoformat()
    file_path = safe_entry_path(date_str, DATA_DIR)

    if file_path.exists():
        try:
            async with aiofiles.open(file_path, "r", encoding=ENCODING) as fh:
                md_content = await fh.read()
        except OSError as exc:
            raise HTTPException(status_code=500, detail="Could not read entry") from exc
        frontmatter, body = split_frontmatter(md_content)
        meta = parse_frontmatter(frontmatter) if frontmatter else {}
        prompt, entry = parse_entry(body)
        if not prompt and not entry:
            entry = body.strip()
        category = meta.get("category", "")
        wotd = meta.get("wotd", "")
    else:
        prompt = ""
        category = ""
        entry = ""
        wotd = ""

    return templates.TemplateResponse(
        request,
        "echo_journal.html",
        {
            "request": request,
            "prompt": prompt,
            "category": category,
            "date": date_str,
            "content": entry,
            "readonly": False,  # Explicit
            "active_page": "home",
            "wotd": wotd,
        },
    )


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
    if isinstance(value, list):
        value_str = "[" + ", ".join(map(str, value)) + "]"
    else:
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


def _with_updated_tags(frontmatter: str | None, tags: list[str]) -> str | None:
    return _update_field(frontmatter, "tags", tags)


@app.post("/entry")
async def save_entry(data: dict):
    """Save a journal entry for the provided date."""
    entry_date = data.get("date")
    content = data.get("content")
    prompt = data.get("prompt")
    category = data.get("category")
    location = data.get("location") or {}
    weather = data.get("weather")
    mood = data.get("mood")
    energy = data.get("energy")

    if not entry_date or not content or not prompt:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing fields"},
        )

    # Ensure /journals exists before attempting to save
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        file_path = safe_entry_path(entry_date, DATA_DIR)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Invalid date"},
        )
    first_save = not file_path.exists()
    if first_save:
        frontmatter = await build_frontmatter(location, weather)
    else:
        frontmatter = await read_existing_frontmatter(file_path)

    # Update or add save_time field
    label = time_of_day_label()
    frontmatter = _with_updated_save_time(frontmatter, label)
    frontmatter = _with_updated_category(frontmatter, category)
    frontmatter = _with_updated_mood(frontmatter, mood)
    frontmatter = _with_updated_energy(frontmatter, energy)

    tags = await fetch_tags(mood or "", energy or "", content)
    frontmatter = _with_updated_tags(frontmatter, tags)

    md_body = f"# Prompt\n{prompt}\n\n# Entry\n{content}"
    if frontmatter is not None:
        md_text = f"---\n{frontmatter}\n---\n{md_body}"
    else:
        md_text = md_body

    lock = SAVE_LOCKS[str(file_path)]
    async with lock:
        async with aiofiles.open(file_path, "w", encoding=ENCODING) as fh:
            await fh.write(md_text)

    await update_photo_metadata(entry_date, file_path)
    await update_song_metadata(entry_date, file_path)
    await update_media_metadata(entry_date, file_path)

    return {"status": "success"}


@app.get("/entry/{entry_date}")
async def get_entry(entry_date: str):
    """Return the full markdown entry for the given date."""
    try:
        file_path = safe_entry_path(entry_date, DATA_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Entry not found") from exc
    if file_path.exists():
        try:
            async with aiofiles.open(file_path, "r", encoding=ENCODING) as fh:
                content = await fh.read()
        except OSError as exc:
            raise HTTPException(status_code=500, detail="Could not read entry") from exc
        return {
            "date": entry_date,
            "content": content,
        }
    return JSONResponse(status_code=404, content={"error": "Entry not found"})


@app.get("/entry")
async def load_entry(entry_date: str):
    """Load the textual content for an entry without headers."""
    try:
        file_path = safe_entry_path(entry_date, DATA_DIR)
    except ValueError:
        return JSONResponse(
            status_code=404, content={"status": "not_found", "content": ""}
        )
    if file_path.exists():
        async with aiofiles.open(file_path, "r", encoding=ENCODING) as fh:
            content = await fh.read()
        # Parse markdown safely to handle different newline styles
        _, body = split_frontmatter(content)
        entry_text = parse_entry(body)[1] or body.strip()
        return {"status": "success", "content": entry_text}
    return JSONResponse(status_code=404, content={"status": "not_found", "content": ""})


async def _load_extra_meta(md_file: Path, meta: dict) -> None:
    """Populate ``meta`` with photo, song and media info if present."""
    if meta.get("photos") in (None, [], "[]"):
        json_path = md_file.with_suffix(".photos.json")
        if json_path.exists():
            try:
                async with aiofiles.open(json_path, "r", encoding=ENCODING) as jh:
                    photos_text = await jh.read()
                if json.loads(photos_text):
                    meta["photos"] = "1"
            except (OSError, ValueError):
                pass
    if not meta.get("songs"):
        songs_path = md_file.with_suffix(".songs.json")
        if songs_path.exists():
            try:
                async with aiofiles.open(songs_path, "r", encoding=ENCODING) as sh:
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
        media_path = md_file.with_suffix(".media.json")
        if media_path.exists():
            try:
                async with aiofiles.open(media_path, "r", encoding=ENCODING) as mh:
                    media_text = await mh.read()
                media_data = json.loads(media_text)
                if media_data:
                    meta["media"] = "1"
            except (OSError, ValueError):
                pass


async def _collect_entries() -> list[dict]:
    """Return a list of entries found under ``DATA_DIR``."""
    entries: list[dict] = []
    for file in DATA_DIR.rglob("*.md"):
        name = file.stem
        try:
            entry_date = datetime.strptime(name, "%Y-%m-%d").date()
        except ValueError:
            entry_date = None
        try:
            async with aiofiles.open(file, "r", encoding=ENCODING) as fh:
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
async def archive_view(
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

    if sort_by == "date":

        def _sort_key(e: dict) -> date:
            return e["date"] or date.min

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
        file_path = safe_entry_path(entry_date, DATA_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Entry not found") from exc
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Entry not found")

    await update_photo_metadata(entry_date, file_path)

    try:
        async with aiofiles.open(file_path, "r", encoding=ENCODING) as fh:
            frontmatter, body = split_frontmatter(await fh.read())
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Could not read entry") from exc

    meta = parse_frontmatter(frontmatter) if frontmatter else {}

    prompt, entry = parse_entry(body)
    if not prompt and not entry:
        entry = body.strip()

    photos = await load_json_file(file_path.with_suffix(".photos.json"))

    songs = await load_json_file(file_path.with_suffix(".songs.json"))

    media = await load_json_file(file_path.with_suffix(".media.json"))

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
            "wotd": meta.get("wotd", ""),
            "photos": photos,
            "songs": songs,
            "media": media,
            "readonly": True,  # Read-only mode for archive
            "active_page": "archive",
        },
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Render the user settings page."""
    return templates.TemplateResponse(
        request,
        "settings.html",
        {"request": request, "active_page": "settings"},
    )


@app.get("/metrics")
async def metrics() -> JSONResponse:
    """Return recent request timing information."""
    return JSONResponse(content={"timings": app.state.request_timings})


async def _gather_entry_stats() -> tuple[dict, int, int, list[date]]:
    """Return aggregated entry counts, total words and entry dates."""
    counts = {
        "week": defaultdict(int),
        "month": defaultdict(int),
        "year": defaultdict(int),
    }
    total_words = 0
    total_entries = 0
    entry_dates: list[date] = []

    for file in DATA_DIR.rglob("*.md"):
        try:
            entry_date = datetime.strptime(file.stem, "%Y-%m-%d").date()
        except ValueError:
            continue

        entry_dates.append(entry_date)

        try:
            async with aiofiles.open(file, "r", encoding=ENCODING) as fh:
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

    return templates.TemplateResponse(
        "stats.html",
        {"request": request, "stats": stats, "active_page": "stats"},
    )


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
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 18,
    }
    headers = {"User-Agent": "EchoJournal/1.0 (you@example.com)"}

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
    if not IMMICH_URL:
        raise HTTPException(status_code=404, detail="Immich not configured")
    headers = {"x-api-key": IMMICH_API_KEY} if IMMICH_API_KEY else {}
    url = f"{IMMICH_URL}/assets/{asset_id}/thumbnail?size={size}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code, detail="Thumbnail fetch failed"
        )
    content_type = resp.headers.get("content-type", "image/jpeg")
    return Response(content=resp.content, media_type=content_type)


@app.get("/api/asset/{asset_id}")
async def proxy_asset(asset_id: str):
    """Fetch a full-size asset from Immich using the API key."""
    if not IMMICH_URL:
        raise HTTPException(status_code=404, detail="Immich not configured")
    headers = {"x-api-key": IMMICH_API_KEY} if IMMICH_API_KEY else {}
    url = f"{IMMICH_URL}/assets/{asset_id}/original"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Asset fetch failed")
    content_type = resp.headers.get("content-type", "application/octet-stream")
    return Response(content=resp.content, media_type=content_type)


@app.post("/api/backfill_songs")
async def backfill_song_metadata() -> dict:
    """Generate missing songs.json files for existing journal entries."""
    songs_logger.info("Starting song metadata backfill")
    added = 0
    for md_file in DATA_DIR.rglob("*.md"):
        songs_path = md_file.with_suffix(".songs.json")
        if songs_path.exists():
            songs_logger.debug("%s already has songs.json", md_file)
            continue
        try:
            datetime.strptime(md_file.stem, "%Y-%m-%d")
        except ValueError:
            songs_logger.debug("Skipping non-entry file %s", md_file)
            continue
        songs_logger.info("Backfilling songs for %s", md_file.stem)
        await update_song_metadata(md_file.stem, md_file)
        if songs_path.exists():
            added += 1
    songs_logger.info("Backfill complete; added %d files", added)
    return {"added": added}
