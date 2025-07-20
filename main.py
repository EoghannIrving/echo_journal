from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.responses import JSONResponse, HTMLResponse
from collections import defaultdict
from datetime import date, datetime
import json

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
    today = date.today()
    date_str = today.isoformat()
    file_path = DATA_DIR / f"{date_str}.md"

    if file_path.exists():
        md_content = file_path.read_text()
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
    date = data.get("date")
    content = data.get("content")
    prompt = data.get("prompt")

    if not date or not content or not prompt:
        return {"status": "error", "message": "Missing fields"}

    file_path = DATA_DIR / f"{date}.md"
    markdown = f"# Prompt\n{prompt}\n\n# Entry\n{content}"
    file_path.write_text(markdown)

    return {"status": "success"}


@app.get("/entry/{date}")
async def get_entry(date: str):
    year = date[:4]
    path = DATA_DIR / year / f"{date}.md"
    if path.exists():
        return {"date": date, "content": path.read_text()}
    return JSONResponse(status_code=404, content={"error": "Entry not found"})

@app.get("/entry")
async def load_entry(date: str):
    file_path = DATA_DIR / f"{date}.md"
    if file_path.exists():
        content = file_path.read_text()
        # Parse markdown to extract entry text only
        parts = content.split("# Entry\n", 1)
        entry_text = parts[1].strip() if len(parts) > 1 else ""
        return {"status": "success", "content": entry_text}
    return {"status": "not_found", "content": ""}

import random

PROMPTS_FILE = Path("/app/prompts.json")

def generate_prompt():
    today = date.today()
    weekday = today.strftime("%A")
    season = get_season(today)

    prompts = json.loads(PROMPTS_FILE.read_text())
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

def get_season(date):
    Y = date.year
    if date >= datetime.date(Y, 3, 1) and date < datetime.date(Y, 6, 1):
        return "Spring"
    elif date >= datetime.date(Y, 6, 1) and date < datetime.date(Y, 9, 1):
        return "Summer"
    elif date >= datetime.date(Y, 9, 1) and date < datetime.date(Y, 12, 1):
        return "Autumn"
    else:
        return "Winter"

@app.get("/archive", response_class=HTMLResponse)
async def archive_view(request: Request):
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
            elif line.strip() == "# Entry":
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
