# Known Bugs

The following issues are still unresolved. Fixed bugs have been moved to [BUGS_FIXED.md](BUGS_FIXED.md).





31. **`load_entry` split assumes Unix newline**
   - The load_entry endpoint splits file contents using `"# Entry\n"`. Files created with Windows newlines (`\r\n`) or without a trailing newline won't parse correctly.
   - Lines:
     ```python
     parts = content.split("# Entry\n", 1)
     ```
     【F:main.py†L181-L182】

33. **Validation errors return HTTP 200**
   - `save_entry` returns an error object but still uses status code 200 when required fields are missing.
   - Lines:
     ```python
     if not entry_date or not content or not prompt:
         return {"status": "error", "message": "Missing fields"}
     ```
     【F:main.py†L134-L135】

34. **Invalid dates accepted**
   - `save_entry` only sanitizes the filename so strings like `2020-13-40` are saved without complaint.
   - Lines:
     ```python
     try:
         file_path = safe_entry_path(entry_date)
     except ValueError:
         return {"status": "error", "message": "Invalid date"}
     md_text = f"# Prompt\n{prompt}\n\n# Entry\n{content}"
     ```
     【F:main.py†L140-L144】

37. **Header parsing is case sensitive**
   - `parse_entry` only recognizes "# Prompt" and "# Entry" exactly; other cases like "# prompt" are ignored.
   - Lines:
     ```python
     if stripped == "# Prompt":
         current_section = "prompt"
     if stripped == "# Entry":
         current_section = "entry"
     ```
     【F:main.py†L78-L83】

39. **Prompts cache never invalidates**
   - `load_prompts` stores the prompts in memory forever; changes to `prompts.json` are ignored after startup.
   - Lines:
     ```python
     if app.state.prompts_cache is None:
         ...
         app.state.prompts_cache = json.loads(prompts_text)
     ```

40. **Multiple save clicks send duplicate requests**
   - The Save button is never disabled during the fetch call, so rapid clicks create several `/entry` POSTs.
   - Lines:
     ```javascript
     saveButton.addEventListener('click', async () => {
       const response = await fetch("/entry", { ... });
     });
     ```
     【F:templates/echo_journal.html†L161-L174】

41. **Archive view reads entire files into memory**
   - Each entry file is fully loaded even though only a preview is needed, which wastes memory for large archives.
   - Lines:
     ```python
     async with aiofiles.open(file, "r", encoding=ENCODING) as fh:
         content = await fh.read()
     entries_by_month[month_key].append((entry_date.isoformat(), content))
     ```
     【F:main.py†L263-L272】


48. **Templates path not configurable**
   - `Jinja2Templates` is created with a hard-coded `"templates"` directory, ignoring `APP_DIR` or other environment settings.
   - Lines:
     ```python
     templates = Jinja2Templates(directory="templates")
     ```
     【F:main.py†L53-L54】

49. **Prompt category never saved**
   - Entries are written without storing the selected prompt category, so the information is lost when reloading.
   - Lines:
     ```python
     md_text = f"# Prompt\n{prompt}\n\n# Entry\n{content}"
     ```
     【F:main.py†L144-L144】

26. **Deprecated TemplateResponse call order**
   - `templates.TemplateResponse` is still called using the old signature where the template name is first. This triggers a deprecation warning from Starlette.
   - Lines:
     ```python
     return templates.TemplateResponse(
         "echo_journal.html",
         {
             "request": request,
             "prompt": prompt,
             "category": "",
             "date": date_str,
             "content": entry,
             "readonly": False,
             "active_page": "home",
         },
     )
     ```
     【F:main.py†L113-L124】

27. **Prompt category never displayed**
   - `generate_prompt` returns a category but the index route ignores it and passes an empty string to the template.
   - Lines:
     ```python
     prompt_data = await generate_prompt()
     prompt = prompt_data["prompt"]
     ...
     "category": "",
     ```
     【F:main.py†L109-L118】


32. **Other routes still use deprecated TemplateResponse signature**
   - `archive_view`, `view_entry`, and `settings_page` pass the template name first instead of the request.
   - Lines:
     ```python
     return templates.TemplateResponse(
         "archives.html",
         {
             "request": request,
             "entries": sorted_entries,
             "active_page": "archive",
         },
     )
     ...
     return templates.TemplateResponse(
         "echo_journal.html",
         {
             "request": request,
             "content": entry,
             "content_html": html_entry,
             "date": entry_date,
             "prompt": prompt,
             "readonly": True,
             "active_page": "archive",
         },
     )
     ...
     return templates.TemplateResponse(
         "settings.html",
         {"request": request, "active_page": "settings"},
     )
     ```
     【F:main.py†L277-L327】

35. **Prompt category never rendered**
   - The journal template lacks any element to show the `category` variable.
   - Lines:
     ```html
     <p id="daily-prompt" class="font-sans font-medium ...">{{ prompt }}</p>
     ```
     【F:templates/echo_journal.html†L18-L21】

36. **Trailing newlines stripped from entries**
   - `parse_entry` removes final blank lines when assembling the prompt and entry sections.
   - Lines:
     ```python
     prompt = "\n".join(prompt_lines).strip()
     entry  = "\n".join(entry_lines).strip()
     ```
     【F:main.py†L90-L91】


47. **Formatting toolbar doesn't resize textarea**
   - The markdown toolbar updates the textarea value but never triggers the oninput handler, so the field height stays wrong after applying formatting.
   - Lines:
     ```javascript
     toolbar.addEventListener('click', (e) => {
       ...
       textarea.value = before + formatted + after;
       textarea.selectionStart = start;
       textarea.selectionEnd = start + formatted.length;
     });
     ```

51. **Malformed filenames hidden from archive**
   - Files with names that don't parse as dates are silently skipped, so they never appear in the archive view.
   - Lines:
     ```python
     for file in DATA_DIR.rglob("*.md"):
         try:
             entry_date = datetime.strptime(file.stem, "%Y-%m-%d").date()
         except ValueError:
             continue  # Skip malformed filenames
     ```

52. **Location may save as 0,0 when saved immediately**
   - The geolocation script populates coordinates asynchronously, so clicking
     Save before it finishes stores zeros for latitude and longitude.
   - Lines:
     ```javascript
     navigator.geolocation.getCurrentPosition(async (pos) => {
       const { latitude, longitude, accuracy } = pos.coords;
       ...
     });
     ...
     const location = locEl ? {
       lat: parseFloat(locEl.dataset.lat || 0),
       lon: parseFloat(locEl.dataset.lon || 0),
       accuracy: parseFloat(locEl.dataset.accuracy || 0),
       label: locEl.dataset.locationName || ''
     } : null;
     ```
     【F:templates/echo_journal.html†L166-L188】

53. **Current month uses server time**
   - `archive_view` expands the section matching the server's current month,
     which can be wrong for users in other time zones.
   - Lines:
     ```python
     current_month = datetime.now().strftime("%Y-%m")
     ```
     【F:main.py†L294-L296】

54. **reverse_geocode unhandled network errors**
   - Failures from the Nominatim API are not caught, returning a 500 response
     instead of a graceful error.
   - Lines:
     ```python
     async with httpx.AsyncClient() as client:
         r = await client.get(url, params=params, headers=headers)
         r.raise_for_status()
     ```
     【F:main.py†L503-L506】

55. **save_time duplication with indented frontmatter**
   - `_with_updated_save_time` only matches lines starting exactly with
     `"save_time:"`, so entries with indented keys get a second `save_time`
     line appended.
   - Lines:
     ```python
     if line.startswith("save_time:"):
         lines[i] = f"save_time: {label}"
     ```
     【F:main.py†L166-L172】

56. **Duplicate dates inflate streak counts**
   - `_calculate_streaks` iterates each entry file without deduplicating dates,
     so multiple files for the same day extend streaks incorrectly.
   - Lines:
     ```python
     for d in entry_dates:
         if prev and d == prev + timedelta(days=1):
             current_day_streak += 1
     ```
     【F:main.py†L430-L435】

