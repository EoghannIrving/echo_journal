"""Echo Journal FastAPI application."""

# pylint: disable=import-error

from collections import defaultdict
from datetime import date, datetime
import json
from pathlib import Path
import random

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse

app = FastAPI()

DATA_DIR = Path("/journals")
PROMPTS_FILE = Path("/app/prompts.json")
STATIC_DIR = Path("/app/static")

# Mount all static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def index(request: Request):
    """Render the journal entry page for the current day."""
    today = date.today()
    date_str = today.isoformat()
    file_path = DATA_DIR / f"{date_str}.md"

    if file_path.exists():
        md_content = file_path.read_text(encoding="utf-8")
        prompt_part = md_content.split("# Prompt\n", 1)[1].split("\n\n# Entry\n", 1)[0].strip()
        entry_part = md_content.split("# Entry\n", 1)[1].strip()
        prompt = prompt_part
        entry = entry_part
    else:
        prompt_data = generate_prompt()
        prompt = prompt_data["prompt"]
        entry = ""

    return templates.TemplateResponse("echo_journal.html", {
        "request": request,
        "prompt": prompt,
        "category": "",  # Optionally store saved category or leave blank for saved entries
        "date": date_str,
        "content": entry,
        "readonly": False  # Explicit
    })

@app.post("/entry")
async def save_entry(data: dict):
    """Save a journal entry for the provided date."""
    entry_date = data.get("date")
    content = data.get("content")
    prompt = data.get("prompt")

    if not entry_date or not content or not prompt:
        return {"status": "error", "message": "Missing fields"}

    file_path = DATA_DIR / f"{entry_date}.md"
    markdown = f"# Prompt\n{prompt}\n\n# Entry\n{content}"
    file_path.write_text(markdown, encoding="utf-8")

    return {"status": "success"}


@app.get("/entry/{entry_date}")
async def get_entry(entry_date: str):
    """Return the full markdown entry for the given date."""
    year = entry_date[:4]
    path = DATA_DIR / year / f"{entry_date}.md"
    if path.exists():
        return {"date": entry_date, "content": path.read_text(encoding="utf-8")}
    return JSONResponse(status_code=404, content={"error": "Entry not found"})

@app.get("/entry")
async def load_entry(entry_date: str):
    """Load the textual content for an entry without headers."""
    file_path = DATA_DIR / f"{entry_date}.md"
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        # Parse markdown to extract entry text only
        parts = content.split("# Entry\n", 1)
        entry_text = parts[1].strip() if len(parts) > 1 else ""
        return {"status": "success", "content": entry_text}
    return {"status": "not_found", "content": ""}



def generate_prompt():
    """Select and return a prompt for the current day."""
    today = date.today()
    weekday = today.strftime("%A")
    season = get_season(today)

    prompts = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
    categories = list(prompts["categories"].keys())

    if not categories:
        return {"category": None, "prompt": "No categories found"}

    category_index = today.day % len(categories)
    category = categories[category_index]

    candidates = prompts["categories"].get(category, [])
    if not candidates:
        return {"category": category.capitalize(), "prompt": "No prompts in this category"}

    prompt_template = random.choice(candidates)
    prompt = prompt_template.replace("{{weekday}}", weekday).replace("{{season}}", season)

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

    for file in DATA_DIR.glob("*.md"):
        try:
            entry_date = datetime.strptime(file.stem, "%Y-%m-%d").date()
        except ValueError:
            continue  # Skip malformed filenames

        month_key = entry_date.strftime("%Y-%m")
        content = file.read_text(encoding="utf-8")
        entries_by_month[month_key].append((entry_date.isoformat(), content))

    # Sort months descending (latest first)
    sorted_entries = dict(sorted(entries_by_month.items(), reverse=True))

    return templates.TemplateResponse("archives.html", {
        "request": request,
        "entries": sorted_entries
    })

@app.get("/view/{entry_date}")
async def view_entry(request: Request, entry_date: str):
    """Display a previously written journal entry."""
    file_path = DATA_DIR / f"{entry_date}.md"
    prompt = ""
    entry = ""
    if file_path.exists():
        lines = file_path.read_text(encoding="utf-8").splitlines()
        current_section = None
        buffer = []

        for line in lines:
            if line.strip() == "# Prompt":
                current_section = "prompt"
                continue
            if line.strip() == "# Entry":
                current_section = "entry"
                continue

            if current_section == "prompt":
                prompt += line.strip()  # Assumes single-line prompt (adjust if multi-line later)
            elif current_section == "entry":
                buffer.append(line)

        entry = "\n".join(buffer).strip()

    return templates.TemplateResponse(
        "echo_journal.html",
        {
            "request": request,
            "content": entry,
            "date": entry_date,
            "prompt": prompt,
            "readonly": True  # Read-only mode for archive
        }
    )
