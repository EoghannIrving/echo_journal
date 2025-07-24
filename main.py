"""Echo Journal FastAPI application."""

# pylint: disable=import-error

import asyncio
import json
import os
import random
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import List, Tuple, Optional

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

# Allow overriding important paths via environment variables for easier testing
# and deployment in restricted environments.
APP_DIR = Path(os.getenv("APP_DIR", "/app"))
DATA_DIR = Path(os.getenv("DATA_DIR", "/journals"))
PROMPTS_FILE = Path(os.getenv("PROMPTS_FILE", str(APP_DIR / "prompts.json")))
STATIC_DIR = Path(os.getenv("STATIC_DIR", str(APP_DIR / "static")))
ENCODING = "utf-8"

# Cache for loaded prompts stored on the FastAPI app state
app.state.prompts_cache = None
PROMPTS_LOCK = asyncio.Lock()
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


def safe_entry_path(entry_date: str) -> Path:
    """Return a normalized path for the given entry date inside DATA_DIR."""
    sanitized = Path(entry_date).name
    sanitized = re.sub(r"[^0-9A-Za-z_-]", "_", sanitized)
    if not sanitized:
        raise ValueError("Invalid entry date")
    path = (DATA_DIR / sanitized).with_suffix(".md")
    # Ensure the path cannot escape DATA_DIR
    try:
        path.resolve().relative_to(DATA_DIR.resolve())
    except ValueError as exc:
        raise ValueError("Invalid entry date") from exc
    return path


def parse_entry(md_content: str) -> Tuple[str, str]:
    """Return (prompt, entry) sections from markdown without raising errors."""
    prompt_lines: List[str] = []
    entry_lines: List[str] = []
    current_section = None
    for line in md_content.splitlines():
        stripped = line.strip()
        if stripped == "# Prompt":
            current_section = "prompt"
            continue
        if stripped == "# Entry":
            current_section = "entry"
            continue
        if current_section == "prompt":
            prompt_lines.append(line.rstrip())
        elif current_section == "entry":
            entry_lines.append(line.rstrip())

    prompt = "\n".join(prompt_lines).strip()
    entry = "\n".join(entry_lines).strip()
    return prompt, entry


def split_frontmatter(text: str) -> Tuple[Optional[str], str]:
    """Return frontmatter and remaining content if present."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1].strip()
            body = parts[2].lstrip("\n")
            return fm, body
    return None, text


async def fetch_weather(lat: float, lon: float) -> Optional[str]:
    """Fetch current weather description from Open-Meteo."""
    if lat == 0 and lon == 0:
        return None
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "current_weather": True}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            cw = data.get("current_weather", {})
            temp = cw.get("temperature")
            code = cw.get("weathercode")
            if temp is not None and code is not None:
                return f"{temp}°C code {code}"
    except (httpx.HTTPError, ValueError):
        # Network issues or JSON parsing errors
        return None
    return None


async def build_frontmatter(location: dict) -> str:
    """Return a YAML frontmatter string based on the provided location."""
    lat = float(location.get("lat") or 0)
    lon = float(location.get("lon") or 0)
    label = location.get("label") or ""
    weather = await fetch_weather(lat, lon)

    lines = []
    if label:
        lines.append(f"location: {label}")
    if weather:
        lines.append(f"weather: {weather}")
    lines.append("photos: []")
    return "\n".join(lines)


async def read_existing_frontmatter(file_path: Path) -> Optional[str]:
    """Return frontmatter from the given file path if present."""
    try:
        async with aiofiles.open(file_path, "r", encoding=ENCODING) as fh:
            existing = await fh.read()
        frontmatter, _ = split_frontmatter(existing)
        return frontmatter
    except OSError:
        return None


@app.get("/")
async def index(request: Request):
    """Render the journal entry page for the current day."""
    today = date.today()
    date_str = today.isoformat()
    file_path = safe_entry_path(date_str)

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
        file_path = safe_entry_path(entry_date)
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
        file_path = safe_entry_path(entry_date)
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
        file_path = safe_entry_path(entry_date)
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


async def load_prompts():
    """Load and cache journal prompts."""
    if app.state.prompts_cache is None:
        async with PROMPTS_LOCK:
            if app.state.prompts_cache is None:
                try:
                    async with aiofiles.open(
                        PROMPTS_FILE, "r", encoding=ENCODING
                    ) as fh:
                        prompts_text = await fh.read()
                    app.state.prompts_cache = json.loads(prompts_text)
                except (FileNotFoundError, json.JSONDecodeError):
                    app.state.prompts_cache = {}
    return app.state.prompts_cache


async def generate_prompt():
    """Select and return a prompt for the current day."""
    today = date.today()
    weekday = today.strftime("%A")
    season = get_season(today)

    prompts = await load_prompts()
    if not prompts:
        return {"category": None, "prompt": "Prompts file not found"}

    categories_dict = prompts.get("categories")
    if not isinstance(categories_dict, dict):
        return {"category": None, "prompt": "No categories found"}

    categories = list(categories_dict.keys())

    if not categories:
        return {"category": None, "prompt": "No categories found"}

    category = random.choice(categories)

    candidates = categories_dict.get(category, [])
    if not candidates:
        return {
            "category": category.capitalize(),
            "prompt": "No prompts in this category",
        }

    prompt_template = random.choice(candidates)
    prompt = prompt_template.replace("{{weekday}}", weekday).replace(
        "{{season}}", season
    )

    return {"category": category.capitalize(), "prompt": prompt}


def get_season(target_date):
    """Return the season name for the given date."""
    year = target_date.year
    spring_start = date(year, 3, 1)
    summer_start = date(year, 6, 1)
    autumn_start = date(year, 9, 1)
    winter_start = date(year, 12, 1)

    if spring_start <= target_date < summer_start:
        return "Spring"
    if summer_start <= target_date < autumn_start:
        return "Summer"
    if autumn_start <= target_date < winter_start:
        return "Autumn"
    return "Winter"


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

        entries_by_month[month_key].append((entry_date.isoformat(), content))

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
        file_path = safe_entry_path(entry_date)
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

    prompt, entry = parse_entry(md_content)
    if not prompt and not entry:
        entry = md_content.strip()

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
    headers = {
        "User-Agent": "EchoJournal/1.0 (you@example.com)"
    }

    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()

    return {
        "display_name": data.get("display_name"),
        "city": data.get("address", {}).get("city") or
                data.get("address", {}).get("town") or
                data.get("address", {}).get("village"),
        "region": data.get("address", {}).get("state"),
        "country": data.get("address", {}).get("country")
    }
