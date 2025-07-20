# Known Bugs

The following issues were identified while reviewing the current code base.

1. **Invalid call to `datetime.date`** (fixed)
   - `get_season` previously used `datetime.date` even though `datetime` was imported as the `datetime` class. The code now correctly calls the `date` constructor.
   - Fixed lines:
     ```python
     spring_start = date(year, 3, 1)
     summer_start = date(year, 6, 1)
     ```
     【F:main.py†L121-L125】

2. **Duplicate `PROMPTS_FILE` constant** (fixed)
   - Earlier versions defined `PROMPTS_FILE` twice in `main.py`. The extra
     definition has been removed so the constant appears only once.
   - Current definition:
     ```python
     PROMPTS_FILE = Path("/app/prompts.json")
     ```
     【F:main.py†L18-L20】

3. **Inconsistent entry file paths** (fixed)
   - `get_entry` previously searched in a year subfolder (`/journals/<year>/<date>.md`) while other functions saved entries directly under `/journals/`.
   - `get_entry` now looks in the same location as `save_entry`.
   - Updated lines:
     ```python
     file_path = DATA_DIR / f"{entry_date}.md"
     if file_path.exists():
         return {
             "date": entry_date,
             "content": file_path.read_text(encoding="utf-8"),
         }
     ```
     【F:main.py†L75-L83】

4. **Archive function ignores subdirectories** (fixed)
   - `archive_view` previously scanned only the top-level `DATA_DIR` directory using `glob("*.md")`.
     It now recursively searches with `rglob("*.md")` so entries within year folders are included.
   - Updated lines:
     ```python
     for file in DATA_DIR.rglob("*.md"):
     ```
     【F:main.py†L150-L158】


5. **Unsanitized date parameter allows path traversal** (fixed)
   - Endpoints previously built file paths directly from user input, allowing `../` sequences to escape the journals directory.
   - All routes now use `safe_entry_path` to sanitize and validate paths.
   - Updated lines:
     ```python
     file_path = safe_entry_path(entry_date)
     ```
     【F:main.py†L102-L118】

6. **Prompt inserted into JavaScript without proper escaping** (fixed)
   - `echo_journal.html` previously embedded the prompt using `{{ prompt | escape }}` inside a template literal.
   - If the prompt contained backticks or `${}`, it could break the script or enable XSS.
   - The template now uses the safer `tojson` filter when embedding the prompt.
   - Updated line:
     ```html
     const prompt = {{ prompt | tojson }};
     ```
     【F:templates/echo_journal.html†L90-L92】

7. **Index parsing assumes perfect file formatting**
   - The `index` function splits the saved Markdown using hard-coded markers.
   - If a file is missing a section header, the `split()[1]` calls will raise `IndexError`.
   - Lines:
     ```python
     md_content.split("# Prompt\n", 1)[1]
     md_content.split("# Entry\n", 1)[1]
     ```
     【F:main.py†L28-L33】

8. **`generate_prompt` lacks error handling** (fixed)
   - The function now catches `FileNotFoundError` and `JSONDecodeError` when
     loading `prompts.json`.
   - Updated lines:
     ```python
     try:
         prompts_text = PROMPTS_FILE.read_text(encoding="utf-8")
         prompts = json.loads(prompts_text)
     except FileNotFoundError:
         return {"category": None, "prompt": "Prompts file not found"}
     except json.JSONDecodeError:
         return {"category": None, "prompt": "Invalid prompts file"}
     ```
     【F:main.py†L106-L112】

9. **Missing data directory creation** (fixed)
   - `save_entry` now ensures the `/journals` folder exists before writing.
   - Updated lines:
     ```python
     # Ensure /journals exists before attempting to save
     DATA_DIR.mkdir(parents=True, exist_ok=True)
     file_path = DATA_DIR / f"{entry_date}.md"
     markdown = f"# Prompt\n{prompt}\n\n# Entry\n{content}"
     file_path.write_text(markdown, encoding="utf-8")
     ```
     【F:main.py†L60-L70】

10. **`view_entry` returns success even when file missing** (fixed)
   - The endpoint now checks for the file and raises `HTTPException(status_code=404)` when not found.
   - Updated lines:
     ```python
     if not file_path.exists():
         raise HTTPException(status_code=404, detail="Entry not found")
     ```
     【F:main.py†L212-L219】

11. **`view_entry` assumes single-line prompt** (fixed)
   - The parser previously appended lines without newlines. It now accumulates lines and joins them preserving line breaks.
   - Updated lines:
     ```python
     if current_section == "prompt":
         prompt_lines.append(line.rstrip())
     ```
     【F:main.py†L229-L233】

12. **`load_entry` returns HTTP 200 on missing file** (fixed)
   - The endpoint now returns a proper 404 JSON response when the entry does not exist.
   - Updated lines:
     ```python
     if file_path.exists():
         ...
         return {"status": "success", "content": entry_text}
     return JSONResponse(status_code=404, content={"status": "not_found", "content": ""})
     ```
     【F:main.py†L86-L96】

13. **Biased category selection in `generate_prompt`** (fixed)
   - The category used to be chosen with `today.day % len(categories)`, causing predictable repetition.
   - The function now selects a category randomly:
     ```python
     category = random.choice(categories)
     ```
     【F:main.py†L157-L158】

14. **Blocking file I/O in async endpoints** (fixed)
   - The application now uses `aiofiles` for all file reads and writes to avoid blocking the event loop.
   - Updated lines:
     ```python
     async with aiofiles.open(file_path, "r", encoding="utf-8") as fh:
         md_content = await fh.read()
     async with aiofiles.open(file_path, "w", encoding="utf-8") as fh:
         await fh.write(markdown)
     ```
     【F:main.py†L30-L69】

15. **Prompts file reloaded on every request** (fixed)
   - Journal prompts are now loaded once and cached in `app.state.prompts_cache`.
   - Updated lines:
     ```python
     async with PROMPTS_LOCK:
         prompts_text = await fh.read()
     ```
     【F:main.py†L116-L134】

16. **Outdated project structure in README** (fixed)
   - The README lists files that do not actually exist and shows `echo_journal.html` under `static/` instead of `templates/`.
   - Lines:
     ```
     ├── static
     │   ├── echo_journal.html
     │   └── style.css
     ├── templates
     │   └── index.html  # (optional for Jinja2 template rendering)
    ├── README.md
    └── ROADMAP.md
    ```
    【F:README.md†L18-L27】

17. **README storage path inconsistent with code** (fixed)
   - Documentation claims entries are stored in `/journals/YYYY/YYYY-MM-DD.md`, but `save_entry` actually writes to `/journals/<date>.md` with no year subfolder.
   - README lines:
     ```
     - Markdown entry storage (`/journals/YYYY/YYYY-MM-DD.md`) on NAS via Docker volume
     ```
     【F:README.md†L6-L11】
   - Code lines:
     ```python
     file_path = DATA_DIR / f"{date}.md"
     ```
     【F:main.py†L57-L58】

18. **Inconsistent file encoding handling** (fixed)
   - Some functions call `read_text()` without specifying an encoding while others pass `encoding="utf-8"`. This may lead to decoding issues on systems with a different default encoding.
   - Examples:
     ```python
     md_content = file_path.read_text()
     content = file.read_text(encoding="utf-8")
     lines = file_path.read_text(encoding="utf-8").splitlines()
     ```
     【F:main.py†L28-L33】【F:main.py†L128-L149】

19. **`date` class shadowed in `save_entry`** (fixed)
   - The parameter `date` in `save_entry` obscures the imported `date` class from `datetime`, which can be confusing and may lead to mistakes if the function later needs the class.
   - Lines:
     ```python
     async def save_entry(data: dict):
         date = data.get("date")
     ```
     【F:main.py†L48-L52】
