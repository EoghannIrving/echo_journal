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
