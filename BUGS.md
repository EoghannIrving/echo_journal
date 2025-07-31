# Known Bugs

The following issues are still unresolved. Fixed bugs have been moved to [BUGS_FIXED.md](BUGS_FIXED.md).


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

