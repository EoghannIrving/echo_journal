# Fixed Bugs

The following issues were identified and subsequently resolved.

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
     PROMPTS_FILE = Path("/app/prompts.yaml")
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
   - The function now catches `FileNotFoundError` and `YAMLError` when
     loading `prompts.yaml`.
   - Updated lines:
     ```python
     try:
         prompts_text = PROMPTS_FILE.read_text(encoding="utf-8")
         prompts = yaml.safe_load(prompts_text)
     except FileNotFoundError:
         return {"category": None, "prompt": "Prompts file not found"}
     except yaml.YAMLError:
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
   - If `prompts.yaml` lacked the `categories` key, `generate_prompt` raised a `KeyError` when accessing `prompts["categories"].keys()`.
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

26. **Rendered Markdown not sanitized** (fixed)
   - `view_entry` converted Markdown to HTML without cleaning it. Combined with
     the `safe` filter in the template, this allowed arbitrary HTML injection.
   - The HTML output is now sanitized using `bleach.clean` before rendering.
   - Updated lines:
     ```python
     html_entry = markdown.markdown(entry)
     html_entry = bleach.clean(
         html_entry,
         tags=bleach.sanitizer.ALLOWED_TAGS.union({"p", "pre"}),
         attributes=bleach.sanitizer.ALLOWED_ATTRIBUTES,
     )
     ```
    【F:main.py†L307-L312】

27. **File I/O errors not handled** (fixed)
   - `get_entry` now catches `OSError` when reading entry files and returns a 500 error instead of crashing.
   - Updated lines:
     ```python
     try:
         async with aiofiles.open(file_path, "r", encoding=ENCODING) as fh:
             content = await fh.read()
     except OSError as exc:
         raise HTTPException(status_code=500, detail="Could not read entry") from exc
     ```
    【F:main.py†L160-L166】

28. **Index route doesn't handle read errors** (fixed)
   - Opening today's entry file could raise an uncaught ``OSError`` and crash the application.
     The index route now catches file read errors and returns an HTTP 500 response instead.
   - Fixed lines:
     ```python
     try:
         async with aiofiles.open(file_path, "r", encoding=ENCODING) as fh:
             md_content = await fh.read()
     except OSError as exc:
         raise HTTPException(status_code=500, detail="Could not read entry") from exc
    ```
    【F:main.py†L103-L108】


29. **Archive view read errors unhandled** (fixed)
   - Unreadable files in the journals directory would raise ``OSError`` and
     crash the ``/archive`` route. The function now skips files it cannot read
     instead of failing the request.
   - Fixed lines:
     ```python
     try:
         async with aiofiles.open(file, "r", encoding=ENCODING) as fh:
             content = await fh.read()
     except OSError:
         # Skip unreadable files instead of failing the entire request
         continue
    ```
    【F:main.py†L278-L283】

30. **`view_entry` lacks file error handling** (fixed)
   - The view route now catches read errors and returns a 500 status instead of crashing.
   - Fixed lines:
     ```python
     try:
         async with aiofiles.open(file_path, "r", encoding=ENCODING) as fh:
             md_content = await fh.read()
     except OSError as exc:
         raise HTTPException(status_code=500, detail="Could not read entry") from exc
     ```
    【F:main.py†L340-L345】

31. **Concurrent saves may overwrite each other** (fixed)
   - `save_entry` now acquires an asyncio lock per file path so simultaneous
     requests cannot clobber the same entry.
   - Fixed lines:
     ```python
     lock = SAVE_LOCKS[str(file_path)]
     async with lock:
         async with aiofiles.open(file_path, "w", encoding=ENCODING) as fh:
             await fh.write(md_text)
     ```
     【F:main.py†L178-L182】

30. **Archive page entries unsorted within month** (fixed)
   - Entries are collected and globally sorted by date before grouping, so each
     month's list is now in descending order.
   - Fixed lines:
     ```python
     all_entries.sort(key=lambda e: e["date"], reverse=True)
     ...
     entries_by_month[month_key].append(
         (entry["date"].isoformat(), entry["prompt"], entry["meta"])
     )
     ```
     【F:main.py†L278-L296】

42. **`JOURNALS_DIR` docs mismatch code** (fixed)
  - Docs no longer treat `JOURNALS_DIR` as a runtime setting. It only affects
    the Docker volume mount.
  - When using Docker Compose, set `JOURNALS_DIR` to choose the host path
    mounted at `/journals`.

43. **Double `.md` extension possible** (fixed)
   - `safe_entry_path` now uses `with_suffix` so existing `.md` extensions are
     replaced rather than appended.
   - Fixed lines:
     ```python
    path = (data_dir / sanitized).with_suffix(".md")
    ```
    【F:file_utils.py†L7-L13】

44. **`load_entry` split assumes Unix newline** (fixed)
   - The endpoint now parses files using `split_frontmatter` and `parse_entry`,
     handling Windows newlines and missing trailing newlines.
   - Fixed lines:
     ```python
     _, body = split_frontmatter(content)
     entry_text = parse_entry(body)[1] or body.strip()
     ```
    【F:main.py†L250-L255】

45. **Validation errors return HTTP 200** (fixed)
   - `save_entry` now returns HTTP 400 when required fields are missing or the
     provided date is invalid.
   - Fixed lines:
     ```python
     if not entry_date or not content or not prompt:
         return JSONResponse(
             status_code=400,
             content={"status": "error", "message": "Missing fields"},
         )
     ...
     except ValueError:
         return JSONResponse(
             status_code=400,
             content={"status": "error", "message": "Invalid date"},
         )
     ```
    【F:main.py†L183-L198】

46. **Invalid dates accepted** (fixed)
   - `safe_entry_path` now validates the date string using `datetime.strptime`.
     Invalid values cause `save_entry` to return HTTP 400 instead of writing a file.
   - Fixed lines:
     ```python
     try:
         datetime.strptime(sanitized, "%Y-%m-%d")
     except ValueError as exc:
         raise ValueError("Invalid entry date") from exc
     ```
    【F:file_utils.py†L20-L23】

47. **Header parsing is case sensitive** (fixed)
   - `parse_entry` now normalizes header lines to lowercase so variations like "# prompt" are recognized.
   - Fixed lines:
     ```python
         stripped = line.strip()
         lowered = stripped.lower()
         if lowered == "# prompt":
             current_section = "prompt"
         if lowered == "# entry":
             current_section = "entry"
    ```
    【F:file_utils.py†L39-L45】

39. **Prompts cache never invalidates** (fixed)
   - ``load_prompts`` now checks the modification time of ``PROMPTS_FILE`` and reloads
     the prompts whenever the file changes.
   - Fixed lines:
     ```python
     try:
         mtime = PROMPTS_FILE.stat().st_mtime
     except FileNotFoundError:
         mtime = None
     if (
         _prompts_cache["data"] is None
         or _prompts_cache.get("mtime") != mtime
     ):
         async with _prompts_lock:
             if (
                 _prompts_cache["data"] is None
                 or _prompts_cache.get("mtime") != mtime
             ):
                 try:
                     async with aiofiles.open(PROMPTS_FILE, "r", encoding=ENCODING) as fh:
                         prompts_text = await fh.read()
                     _prompts_cache["data"] = json.loads(prompts_text)
                     _prompts_cache["mtime"] = mtime
                 except (FileNotFoundError, json.JSONDecodeError):
                     _prompts_cache["data"] = {}
                     _prompts_cache["mtime"] = mtime
    ```
    【F:prompt_utils.py†L16-L42】

40. **Multiple save clicks send duplicate requests** (fixed)
   - The save button is now disabled during the network request to prevent
     duplicate POSTs when clicked rapidly or triggered via keyboard shortcut.
   - Fixed lines:
     ```javascript
     if (saveButton.disabled) {
       return;
     }
     saveButton.disabled = true;
     ...
     saveButton.disabled = false;
     ```
    【F:templates/echo_journal.html†L163-L216】

41. **Archive view reads entire files into memory** (fixed)
   - `_collect_entries` used to read each entry file entirely even though only
     the frontmatter and prompt are needed for the archive preview. The function
     now reads at most 8192 bytes to avoid loading large files into memory.
   - Fixed lines:
     ```python
         async with aiofiles.open(file, "r", encoding=ENCODING) as fh:
-            content = await fh.read()
+            content = await fh.read(8192)
    ```
    【F:main.py†L301-L304】

48. **Templates path not configurable** (fixed)
   - `Jinja2Templates` used a hard-coded `"templates"` directory. The
     path now comes from `TEMPLATES_DIR` so it can be overridden via an
     environment variable.
   - Fixed lines:
     ```python
     templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
     ```
     【F:main.py†L101-L102】
     ```python
    TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", str(APP_DIR / "templates")))
    ```
    【F:config.py†L11-L12】

49. **Prompt category never saved** (fixed)
   - Entries were saved without storing the selected prompt category.
     The save endpoint now persists the category in frontmatter when provided.
   - Fixed lines:
     ```python
     frontmatter = _with_updated_save_time(frontmatter, label)
     frontmatter = _with_updated_category(frontmatter, category)
     ```
     【F:main.py†L224-L227】
     ```javascript
     const category = {{ category | tojson }};
     ...
    body: JSON.stringify({ date, content, prompt, category, location })
    ```
    【F:templates/echo_journal.html†L173-L187】

50. **Deprecated TemplateResponse call order** (fixed)
   - The index route now calls `TemplateResponse` with the request object first,
     following the updated Starlette signature.
   - Fixed lines:
     ```python
     return templates.TemplateResponse(
         request,
         "echo_journal.html",
         {
             "request": request,
             "prompt": prompt,
             "category": "",
             "date": date_str,
             "content": entry,
             "readonly": False,
             "active_page": "home",
             "wotd": wotd,
         },
     )
     ```
    【F:main.py†L147-L160】

51. **Prompt category never displayed** (fixed)
   - `generate_prompt` returns a category, but the index route ignored it and
     sent an empty string to the template. The route now passes the real
     category and reads it from saved entries.
   - Fixed lines:
     ```python
         prompt_data = await generate_prompt()
         prompt = prompt_data["prompt"]
         category = prompt_data.get("category", "")
     ```
     ```python
         category = meta.get("category", "")
         wotd = meta.get("wotd", "")
     ```
    【F:main.py†L138-L155】

52. **Other routes used deprecated TemplateResponse call order** (fixed)
   - `archive_view`, `archive_entry`, and `settings_page` now pass the
     request object as the first argument to `TemplateResponse`.
   - Fixed lines:
     ```python
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
     ```
    【F:main.py†L379-L389】

53. **Prompt category never rendered** (fixed)
   - The journal page now shows the prompt's category beneath the prompt text.
   - Fixed lines:
     ```html
     {% if category %}
     <p id="prompt-category" class="text-sm italic text-gray-600 dark:text-gray-400 mb-1">{{ category }}</p>
     {% endif %}
     ```
     【F:templates/echo_journal.html†L20-L22】


36. **Trailing newlines stripped from entries** (fixed)
   - `parse_entry` removed final blank lines when assembling the prompt and entry sections.
   - Fixed lines:
     ```python
     prompt = "\n".join(prompt_lines)
     entry = "\n".join(entry_lines)
     ```
     【F:file_utils.py†L52-L53】
54. **Malformed filenames hidden from archive** (fixed)
   - `_collect_entries` previously skipped files whose names did not parse as dates.
     These entries now appear in an "Unknown" month section of the archive.
   - Fixed lines:
     ```python
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
     ```
     【F:main.py†L316-L335】
     ```python
         if entry["date"]:
             month_key = entry["date"].strftime("%Y-%m")
             date_str = entry["date"].isoformat()
         else:
             month_key = "Unknown"
             date_str = entry["name"]
         entries_by_month[month_key].append(
             (date_str, entry["prompt"], entry["meta"])
         )
    ```
    【F:main.py†L374-L383】

55. **Location may save as 0,0 when saved immediately** (fixed)
   - The geolocation script populates coordinates asynchronously, so clicking
     Save before it finished would store zeros for latitude and longitude.
     The save handler now checks that coordinates exist before sending them.
   - Fixed lines:
     ```javascript
     const locEl = document.getElementById('location-display');
     let location = null;
     if (locEl && locEl.dataset.lat && locEl.dataset.lon) {
       location = {
         lat: parseFloat(locEl.dataset.lat),
         lon: parseFloat(locEl.dataset.lon),
         accuracy: parseFloat(locEl.dataset.accuracy || 0),
         label: locEl.dataset.locationName || ''
       };
     }
    ```
    【F:templates/echo_journal.html†L177-L186】

56. **Current month uses server time** (fixed)
   - `archive_view` previously expanded the section matching the server's
     current month, which could be incorrect for users in other time zones.
     It now opens the most recent month that actually contains entries.
   - Fixed lines:
     ```python
     sorted_entries = dict(sorted(entries_by_month.items(), reverse=True))
     if sorted_entries:
         current_month = next(iter(sorted_entries))
     else:
         current_month = datetime.now().strftime("%Y-%m")
     ```
    【F:main.py†L386-L391】

57. **reverse_geocode unhandled network errors** (fixed)
   - The endpoint now catches HTTP failures from the Nominatim API and returns
     a 502 status instead of crashing.
   - Fixed lines:
     ```python
     try:
         async with httpx.AsyncClient() as client:
             r = await client.get(url, params=params, headers=headers, timeout=10)
             r.raise_for_status()
             data = r.json()
     except (httpx.HTTPError, ValueError) as exc:
         raise HTTPException(status_code=502, detail="Reverse geocoding failed") from exc
     ```
    【F:main.py†L596-L602】

58. **save_time duplication with indented frontmatter** (fixed)
   - `_with_updated_save_time` now matches and replaces a `save_time` key even
     when it is indented. This prevents multiple `save_time` lines from being
     appended.
   - Fixed lines:
     ```python
    stripped = line.lstrip()
    if stripped.startswith("save_time:"):
        indent = line[: len(line) - len(stripped)]
        lines[i] = f"{indent}save_time: {label}"
    ```
    【F:main.py†L169-L175】

59. **Duplicate dates inflate streak counts** (fixed)
   - `_calculate_streaks` now deduplicates dates before computing streaks so
     multiple files for the same day no longer affect the counts.
   - Fixed lines:
     ```python
     unique_dates = sorted(set(entry_dates))
     for d in unique_dates:
         if prev and d == prev + timedelta(days=1):
             current_day_streak += 1
         else:
             current_day_streak = 1 if unique_dates else 0
     ```
     【F:main.py†L521-L531】

