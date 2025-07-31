# Known Bugs

The following issues are still unresolved. Fixed bugs have been moved to [BUGS_FIXED.md](BUGS_FIXED.md).


53. **save_time duplication with indented frontmatter**
   - `_with_updated_save_time` only matches lines starting exactly with
     `"save_time:"`, so entries with indented keys get a second `save_time`
     line appended.
   - Lines:
     ```python
     if line.startswith("save_time:"):
         lines[i] = f"save_time: {label}"
     ```
     【F:main.py†L166-L172】

54. **Duplicate dates inflate streak counts**
   - `_calculate_streaks` iterates each entry file without deduplicating dates,
     so multiple files for the same day extend streaks incorrectly.
   - Lines:
     ```python
     for d in entry_dates:
         if prev and d == prev + timedelta(days=1):
             current_day_streak += 1
     ```
     【F:main.py†L430-L435】

