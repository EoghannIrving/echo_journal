# Known Bugs

The following issues are still unresolved. Fixed bugs have been moved to [BUGS_FIXED.md](BUGS_FIXED.md).

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

28. **Rendered Markdown not sanitized**
   - Entries are converted to HTML with `markdown.markdown` and inserted with the `safe` filter. Malicious HTML is therefore executed when viewing an entry.
   - Lines:
     ```python
     html_entry = markdown.markdown(entry)
     ```
     【F:main.py†L306-L313】
     ```html
     {{ content_html|safe }}
     ```
     【F:templates/echo_journal.html†L38-L39】

29. **Empty sections cause server error**
   - `view_entry` raises a 500 error if either the prompt or entry section is empty even though index handles missing headers gracefully.
   - Lines:
     ```python
     prompt, entry = parse_entry(md_content)
     if not prompt or not entry:
         raise HTTPException(status_code=500, detail="Malformed entry file")
     ```
     【F:main.py†L302-L305】

30. **Archive page entries unsorted within month**
   - `archive_view` sorts months but does not sort entries inside each month, so dates can appear out of order.
   - Lines:
     ```python
     entries_by_month[month_key].append((entry_date.isoformat(), content))
     # ... months sorted only
     sorted_entries = dict(sorted(entries_by_month.items(), reverse=True))
     ```
     【F:main.py†L263-L275】

31. **`load_entry` split assumes Unix newline**
   - The load_entry endpoint splits file contents using `"# Entry\n"`. Files created with Windows newlines (`\r\n`) or without a trailing newline won't parse correctly.
   - Lines:
     ```python
     parts = content.split("# Entry\n", 1)
     ```
     【F:main.py†L181-L182】

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

38. **File I/O errors not handled**
   - `get_entry` opens files without catching `OSError`, so permission issues crash the server.
   - Lines:
     ```python
     async with aiofiles.open(file_path, "r", encoding=ENCODING) as fh:
         content = await fh.read()
     ```
     【F:main.py†L158-L160】

39. **Prompts cache never invalidates**
   - `load_prompts` stores the prompts in memory forever; changes to `prompts.json` are ignored after startup.
   - Lines:
     ```python
     if app.state.prompts_cache is None:
         ...
         app.state.prompts_cache = json.loads(prompts_text)
     ```
     【F:main.py†L187-L200】

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
