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

7. **Index parsing assumes perfect file formatting** (fixed)
   - The `index` function no longer relies on fragile `split()[1]` calls.
   - A new helper `parse_entry` safely extracts sections and falls back to the
     raw content if headers are missing.
   - Updated lines:
     ```python
     prompt, entry = parse_entry(md_content)
     if not prompt and not entry:
         entry = md_content.strip()
     ```
     【F:main.py†L80-L86】

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
   - File reads and writes now consistently specify the encoding using the `ENCODING` constant.
   - Updated definition:
     ```python
     ENCODING = "utf-8"
     ```
     【F:main.py†L23-L27】
   - All `aiofiles.open` calls pass `encoding=ENCODING`.
     【F:main.py†L82-L245】

19. **`date` class shadowed in `save_entry`** (fixed)
   - The parameter `date` in `save_entry` obscures the imported `date` class from `datetime`, which can be confusing and may lead to mistakes if the function later needs the class.
   - Lines:
     ```python
     async def save_entry(data: dict):
         date = data.get("date")
     ```
     【F:main.py†L48-L52】

20. **README port mismatch** (fixed)
  - The README previously instructed users to visit `http://localhost:8000` but `docker-compose.yml` exposes port `8510`.
  - README now shows:
    ```
    Visit `http://localhost:8510` from any device on your LAN.
    ```
    【F:README.md†L60-L63】
  - Compose lines:
    ```yaml
    ports:
      - "8510:8000"
    ```
    【F:docker-compose.yml†L1-L5】

21. **Prompt category ignored on index page** (fixed)
   - `generate_prompt` returns a category, but `index` sets the `category` template variable to an empty string.
   - Lines:
     ```python
     prompt_data = await generate_prompt()
     prompt = prompt_data["prompt"]
     ...
     "category": "",  # Optionally store saved category or leave blank for saved entries
     ```
     【F:main.py†L87-L95】

22. **`generate_prompt` assumes `categories` key exists** (fixed)
   - If `prompts.json` lacked the `categories` key, `generate_prompt` raised a `KeyError` when accessing `prompts["categories"].keys()`.
   - The function now safely retrieves the dictionary and handles missing or invalid values.
   - Updated lines:
     ```python
     categories_dict = prompts.get("categories")
     if not isinstance(categories_dict, dict):
         return {"category": None, "prompt": "No categories found"}

     categories = list(categories_dict.keys())
     ...
     candidates = categories_dict.get(category, [])
     ```
     【F:main.py†L174-L190】

23. **`safe_entry_path` allows empty filenames** (fixed)
   - Passing an empty `entry_date` results in the path `/journals/.md` because the sanitized name becomes an empty string.
   - The function now rejects empty filenames and raises `ValueError`.
   - Updated lines:
     ```python
     sanitized = Path(entry_date).name
     sanitized = re.sub(r"[^0-9A-Za-z_-]", "_", sanitized)
     if not sanitized:
         raise ValueError("Invalid entry date")
     path = (DATA_DIR / sanitized).with_suffix(".md")
     ```
     【F:main.py†L57-L69】

24. **Save entry script lacks error handling** (fixed)
   - The JavaScript fetch request assumes a JSON response without checking `response.ok` or catching exceptions. Network failures lead to uncaught errors.
   - Lines:
     ```javascript
     const response = await fetch("/entry", {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       body: JSON.stringify({ date, content, prompt })
     });

     const result = await response.json();
     ```
     【F:templates/echo_journal.html†L72-L85】

25. **Textarea doesn't resize on load** (fixed)
   - The textarea expands on user input, but when an existing entry is loaded the `oninput` handler never fires. The field remains at its default height and cuts off longer text until edited.
   - Lines:
     ```html
     <textarea id="journal-text" class="journal-textarea justify-center"
       placeholder="Write freely… describe what happened, how you felt, what you noticed, or anything else that stands out."
       {% if readonly %}readonly{% endif %}
       oninput="this.style.height='auto'; this.style.height=(this.scrollHeight)+'px'"
       rows="4"
     >{{ content }}</textarea>
     ```
     【F:templates/echo_journal.html†L24-L32】

26. **Dark mode toggle has no effect when system already uses dark mode** (fixed)
   - The CSS applies dark colors automatically with the `prefers-color-scheme` media query.
   - The toggle in `settings.html` only toggles a `dark` class, which does not override these rules.
   - Lines:
     ```css
     @media (prefers-color-scheme: dark) {
       body {
         background-color: #222;
         color: #f5f5f5;
       }
     }
     ```
     【F:static/style.css†L20-L25】
   - Toggle script lines:
     ```javascript
     const toggle = document.getElementById('dark-toggle');
     if (toggle) {
       const stored = localStorage.getItem('dark-mode');
       if (stored === 'true') {
         toggle.checked = true;
         document.documentElement.classList.add('dark');
       }
       toggle.addEventListener('change', () => {
         if (toggle.checked) {
           document.documentElement.classList.add('dark');
           localStorage.setItem('dark-mode', 'true');
         } else {
           document.documentElement.classList.remove('dark');
           localStorage.setItem('dark-mode', 'false');
         }
       });
     }
     ```
     【F:templates/settings.html†L28-L52】
