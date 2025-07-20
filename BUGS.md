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

4. **Archive function ignores subdirectories**
   - `archive_view` scans `DATA_DIR.glob("*.md")`. If journal entries were stored in year subfolders, they would not appear in the archive.
   - Lines:
     ```python
     for file in DATA_DIR.glob("*.md"):
     ```
     【F:main.py†L121-L133】


5. **Unsanitized date parameter allows path traversal** (fixed)
   - Date strings are now validated with a regular expression and `datetime.strptime`.
   - Example validation check:
     ```python
     if not valid_entry_date(entry_date):
         return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid date"})
     ```
     【F:main.py†L30-L41】【F:main.py†L80-L82】【F:main.py†L96-L98】【F:main.py†L109-L110】【F:main.py†L194-L205】

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

10. **`view_entry` returns success even when file missing**
   - The endpoint always returns the journal template, leaving `prompt` and `entry` empty instead of sending a 404 for nonexistent dates.
   - Lines:
     ```python
     if file_path.exists():
         lines = file_path.read_text(encoding="utf-8").splitlines()
         ...
     return templates.TemplateResponse(...)
     ```
     【F:main.py†L143-L176】

11. **`view_entry` assumes single-line prompt**
   - When parsing a saved entry, the code concatenates all lines under `# Prompt` without newlines. Multi-line prompts will be collapsed.
   - Lines:
     ```python
     if current_section == "prompt":
         prompt += line.strip()  # Assumes single-line prompt
     ```
     【F:main.py†L161-L163】

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

13. **Biased category selection in `generate_prompt`**
   - The category is chosen using `today.day % len(categories)`. This repeats the same categories on certain days and is predictable.
   - Lines:
     ```python
     category_index = today.day % len(categories)
     category = categories[category_index]
     ```
     【F:main.py†L98-L100】

14. **Blocking file I/O in async endpoints**
   - Functions like `index` and `save_entry` call `read_text()` and `write_text()` directly. These synchronous operations can block the event loop under load.
   - Lines:
     ```python
     md_content = file_path.read_text()
     file_path.write_text(markdown)
     ```
     【F:main.py†L28-L33】【F:main.py†L56-L60】

15. **Prompts file reloaded on every request**
   - `generate_prompt` reads and parses `prompts.json` each time it is called. Caching the file contents would avoid unnecessary disk I/O.
   - Lines:
     ```python
     prompts = json.loads(PROMPTS_FILE.read_text())
     ```
     【F:main.py†L92-L93】

16. **Outdated project structure in README**
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

17. **README storage path inconsistent with code**
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

18. **Inconsistent file encoding handling**
   - Some functions call `read_text()` without specifying an encoding while others pass `encoding="utf-8"`. This may lead to decoding issues on systems with a different default encoding.
   - Examples:
     ```python
     md_content = file_path.read_text()
     content = file.read_text(encoding="utf-8")
     lines = file_path.read_text(encoding="utf-8").splitlines()
     ```
     【F:main.py†L28-L33】【F:main.py†L128-L149】

19. **`date` class shadowed in `save_entry`**
   - The parameter `date` in `save_entry` obscures the imported `date` class from `datetime`, which can be confusing and may lead to mistakes if the function later needs the class.
   - Lines:
     ```python
     async def save_entry(data: dict):
         date = data.get("date")
     ```
     【F:main.py†L48-L52】
