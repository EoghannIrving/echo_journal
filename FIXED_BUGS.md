# Fixed Bugs

The following issues have been resolved.

29. **Empty sections cause server error** (fixed)
   - `view_entry` used to raise a 500 error if either the prompt or entry section was missing. The function now falls back to the raw content when both sections are absent.
   - Fixed lines:
     ```python
     prompt, entry = parse_entry(md_content)
     if not prompt and not entry:
         entry = md_content.strip()
     ```
     【F:main.py†L350-L352】
