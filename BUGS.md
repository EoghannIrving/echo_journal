# Known Bugs

The following issues are still unresolved. Fixed bugs have been moved to [BUGS_FIXED.md](BUGS_FIXED.md).

### Open Issues

- HTTP Basic authentication uses plaintext credentials stored in configuration
- Journal entries are written directly to the final file path without atomic replacement or symlink protection
- Full settings (including API keys and passwords) are logged during load and save operations
- CSRF token cookie is set without the `Secure` attribute
- Location data is inserted into YAML frontmatter without validation; non-numeric latitude/longitude raise `ValueError` and the label is written verbatim
- No rate-limiting on authentication attempts
- Application defaults to `DEBUG` logging level
- Broad `except Exception` block during configuration reload hides underlying issues
- `load_settings` does not handle `yaml.YAMLError`, so malformed configuration files can crash the application
- `build_frontmatter` truncates Wordnik definitions to a single line, losing multi-line explanations【F:src/echo_journal/weather_utils.py†L75-L83】
- Immich API responses are logged in full at debug level, leaking potentially sensitive metadata【F:src/echo_journal/immich_utils.py†L74-L76】
- AI prompt responses are logged verbatim at debug level, exposing generated content【F:src/echo_journal/ai_prompt_utils.py†L117-L118】
- Metadata helper functions write `.photos.json`, `.songs.json`, and `.media.json` directly without atomic replacement or symlink protection【F:src/echo_journal/immich_utils.py†L136-L142】【F:src/echo_journal/jellyfin_utils.py†L190-L196】
- `SAVE_LOCKS` grows without bounds for each unique entry path, allowing memory exhaustion via many distinct dates【F:src/echo_journal/main.py†L212-L213】
- Docker image runs as the `root` user because no non-privileged `USER` is specified【F:Dockerfile†L7-L18】
- `docker-compose.yml` uses `TZ:${TZ}` instead of `TZ=${TZ}`, so the timezone variable may not be set correctly【F:docker-compose.yml†L11】
