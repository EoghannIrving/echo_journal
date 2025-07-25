"""Echo Journal FastAPI application."""

# pylint: disable=import-error

import asyncio
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from typing import Dict

import logging
import time

import markdown
import bleach

import aiofiles
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import DATA_DIR, STATIC_DIR, ENCODING
from file_utils import (
    safe_entry_path,
    parse_entry,
    read_existing_frontmatter,
    split_frontmatter,
    parse_frontmatter,
    format_weather,
)
from prompt_utils import generate_prompt
from weather_utils import build_frontmatter


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

# Setup basic logging for timing middleware
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ej.timing")

# Store recent request timings on the FastAPI state
MAX_TIMINGS = 50
app.state.request_timings = []

# Locks for concurrent saves keyed by entry path
SAVE_LOCKS = defaultdict(asyncio.Lock)

# Mount all static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")


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
        prompt, entry = parse_entry(md_content)
        if not prompt and not entry:
            entry = md_content.strip()
    else:
        prompt_data = await generate_prompt()
        prompt = prompt_data["prompt"]
        entry = ""

    return templates.TemplateResponse(
        "echo_journal.html",
        {
            "request": request,
            "prompt": prompt,
            "category": "",  # Optionally store saved category or leave blank for saved entries
            "date": date_str,
            "content": entry,
            "readonly": False,  # Explicit
            "active_page": "home",
        },
    )


@app.post("/entry")
async def save_entry(data: dict):
    """Save a journal entry for the provided date."""
    entry_date = data.get("date")
    content = data.get("content")
    prompt = data.get("prompt")
    location = data.get("location") or {}

    if not entry_date or not content or not prompt:
        return {"status": "error", "message": "Missing fields"}

    # Ensure /journals exists before attempting to save
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        file_path = safe_entry_path(entry_date, DATA_DIR)
    except ValueError:
        return {"status": "error", "message": "Invalid date"}
    first_save = not file_path.exists()
    if first_save:
        frontmatter = await build_frontmatter(location)
    else:
        frontmatter = await read_existing_frontmatter(file_path)

    md_body = f"# Prompt\n{prompt}\n\n# Entry\n{content}"
    if frontmatter is not None:
        md_text = f"---\n{frontmatter}\n---\n{md_body}"
    else:
        md_text = md_body

    lock = SAVE_LOCKS[str(file_path)]
    async with lock:
        async with aiofiles.open(file_path, "w", encoding=ENCODING) as fh:
            await fh.write(md_text)

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
        # Parse markdown to extract entry text only
        parts = content.split("# Entry\n", 1)
        entry_text = parts[1].strip() if len(parts) > 1 else ""
        return {"status": "success", "content": entry_text}
    return JSONResponse(status_code=404, content={"status": "not_found", "content": ""})


@app.get("/archive", response_class=HTMLResponse)
async def archive_view(request: Request):
    """Render an archive of all journal entries grouped by month."""
    entries_by_month = defaultdict(list)

    # Recursively gather markdown files to include any entries stored in
    # subdirectories such as year folders
    for file in DATA_DIR.rglob("*.md"):
        try:
            entry_date = datetime.strptime(file.stem, "%Y-%m-%d").date()
        except ValueError:
            continue  # Skip malformed filenames

        month_key = entry_date.strftime("%Y-%m")

        try:
            async with aiofiles.open(file, "r", encoding=ENCODING) as fh:
                content = await fh.read()
        except OSError:
            # Skip unreadable files instead of failing the entire request
            continue

        prompt, _ = parse_entry(content)
        entries_by_month[month_key].append((entry_date.isoformat(), prompt))

    # Sort months descending (latest first)
    sorted_entries = dict(sorted(entries_by_month.items(), reverse=True))

    return templates.TemplateResponse(
        "archives.html",
        {
            "request": request,
            "entries": sorted_entries,
            "active_page": "archive",
        },
    )


@app.get("/view/{entry_date}")
async def view_entry(request: Request, entry_date: str):
    """Display a previously written journal entry."""
    try:
        file_path = safe_entry_path(entry_date, DATA_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Entry not found") from exc
    prompt = ""
    entry = ""
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Entry not found")

    try:
        async with aiofiles.open(file_path, "r", encoding=ENCODING) as fh:
            md_content = await fh.read()
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Could not read entry") from exc

    frontmatter, body = split_frontmatter(md_content)
    meta = parse_frontmatter(frontmatter) if frontmatter else {}
    location = meta.get("location", "")
    weather_raw = meta.get("weather", "")
    weather = format_weather(weather_raw) if weather_raw else ""

    prompt, entry = parse_entry(body)
    if not prompt and not entry:
        entry = body.strip()

    html_entry = markdown.markdown(entry)
    html_entry = bleach.clean(
        html_entry,
        tags=bleach.sanitizer.ALLOWED_TAGS.union({"p", "pre"}),
        attributes=bleach.sanitizer.ALLOWED_ATTRIBUTES,
    )

    return templates.TemplateResponse(
        "echo_journal.html",
        {
            "request": request,
            "content": entry,
            "content_html": html_entry,
            "date": entry_date,
            "prompt": prompt,
            "location": location,
            "weather": weather,
            "readonly": True,  # Read-only mode for archive
            "active_page": "archive",
        },
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Render the user settings page."""
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "active_page": "settings"},
    )


@app.get("/metrics")
async def metrics() -> JSONResponse:
    """Return recent request timing information."""
    return JSONResponse(content={"timings": app.state.request_timings})


@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    """Render journal statistics including entry counts and words."""
    counts = {
        "week": defaultdict(int),
        "month": defaultdict(int),
        "year": defaultdict(int),
    }
    total_words = 0
    total_entries = 0

    for file in DATA_DIR.rglob("*.md"):
        try:
            entry_date = datetime.strptime(file.stem, "%Y-%m-%d").date()
        except ValueError:
            continue

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

    stats: Dict[str, object] = {
        "weeks": sorted(counts["week"].items(), reverse=True),
        "months": sorted(counts["month"].items(), reverse=True),
        "years": sorted(counts["year"].items(), reverse=True),
        "total_entries": total_entries,
        "total_words": total_words,
        "average_words": round(total_words / total_entries, 1)
        if total_entries
        else 0,
    }

    return templates.TemplateResponse(
        "stats.html",
        {"request": request, "stats": stats, "active_page": "stats"},
    )


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

    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()

    return {
        "display_name": data.get("display_name"),
        "city": data.get("address", {}).get("city")
        or data.get("address", {}).get("town")
        or data.get("address", {}).get("village"),
        "region": data.get("address", {}).get("state"),
        "country": data.get("address", {}).get("country"),
    }
