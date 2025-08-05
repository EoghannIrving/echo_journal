# Known Bugs

The following issues are still unresolved. Fixed bugs have been moved to [BUGS_FIXED.md](BUGS_FIXED.md).

### Open Issues

- Modules such as `weather_utils` import `httpx`, but the dependency isn't installed, leading to runtime `ModuleNotFoundError` errors during tests【F:src/echo_journal/weather_utils.py†L3-L7】【e80705†L116-L126】
- `file_utils` relies on `aiofiles`, yet the package is missing from the environment, causing import failures【F:src/echo_journal/file_utils.py†L9-L10】【e80705†L103-L104】
- `settings_utils` imports `yaml`, which is absent and triggers a `ModuleNotFoundError` when tests run【F:src/echo_journal/settings_utils.py†L9】【e80705†L112-L114】
- `load_env` naively splits on the first `=` and cannot handle quoted values or keys containing `=` characters【F:src/echo_journal/env_utils.py†L20-L24】
- `ENV_PATH` is defined as a relative `.env` path, so calls from other working directories fail to locate the file【F:src/echo_journal/env_utils.py†L7】
- `fetch_date_fact` requests the Numbers API over unencrypted HTTP, exposing the request to interception【F:src/echo_journal/numbers_utils.py†L15】
- The Numbers API call passes `json=True`, but the service expects a flag-like `?json` parameter, which may return non‑JSON responses【F:src/echo_journal/numbers_utils.py†L18】
- `build_frontmatter` truncates Wordnik definitions to a single line, losing multi-line explanations【F:src/echo_journal/weather_utils.py†L75-L79】
- `save_settings` merges incoming values without type validation, potentially writing unexpected types to `settings.yaml`【F:src/echo_journal/settings_utils.py†L86-L93】
- `_iter_items` in `jellyfin_utils` loops endlessly if the API continually returns full pages at or after the target date because the `while True` loop lacks a hard stop【F:src/echo_journal/jellyfin_utils.py†L35-L46】
