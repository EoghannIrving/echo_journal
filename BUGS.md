# Known Bugs

The following issues are still unresolved. Fixed bugs have been moved to [BUGS_FIXED.md](BUGS_FIXED.md).


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

