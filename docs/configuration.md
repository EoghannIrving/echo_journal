# Configuration

On startup the application looks for a `settings.yaml` file in `<DATA_DIR>/.settings/settings.yaml` (default `/journals/.settings/settings.yaml`). If it is missing a warning is logged noting the expected path and the app falls back to environment variables. The `settings.yaml` file configures optional integrations and runtime paths. It is the authoritative source for these values:

| Variable | Purpose | Notes / Defaults |
| --- | --- | --- |
| `DATA_DIR` | Internal application path. | Default `/journals`. |
| `APP_DIR` | Internal application directory. | Automatically derived from the installed package; override with `APP_DIR` env var if needed. |
| `PROMPTS_FILE` | Location of YAML prompts file. | Default `<APP_DIR>/prompts.yaml`. |
| `STATIC_DIR` | Directory for static assets. | Default `<APP_DIR>/static`. |
| `TEMPLATES_DIR` | Directory for Jinja2 templates. | Default `<APP_DIR>/templates`. |
| `WORDNIK_API_KEY` | Enables the Wordnik "word of the day" prompt. | |
| `OPENAI_API_KEY` | Enables AI-generated prompts via the OpenAI API. | Usage may incur costs and is subject to OpenAI's rate limits. |
| `IMMICH_URL` | URL of your Immich server. | |
| `IMMICH_API_KEY` | API key for Immich. | |
| `IMMICH_TIME_BUFFER` | Hour window to fetch photos. | Default `15`. |
| `JELLYFIN_URL` | Base URL of Jellyfin server. | |
| `JELLYFIN_API_KEY` | API key for Jellyfin. | |
| `JELLYFIN_USER_ID` | Jellyfin user ID. | |
| `JELLYFIN_PAGE_SIZE` | Pagination size for Jellyfin API. | Default `200`. |
| `JELLYFIN_PLAY_THRESHOLD` | Percent threshold for "played". | Default `90`. |
| `NOMINATIM_USER_AGENT` | Identifies your app when calling the Nominatim reverse geocoding API. | Include contact info per the usage policy. |
| `LOG_LEVEL` | Logging verbosity. | Default `DEBUG`. |
| `LOG_FILE` | Path to log file. | Default `/journals/.logs/echo_journal.log`; if empty, logs to stderr. |
| `LOG_MAX_BYTES` | Max size before log rotation. | Default `1,048,576`. |
| `LOG_BACKUP_COUNT` | Number of rotated log files. | Default `3`. |
| `ECHO_JOURNAL_HOST` | Network interface to bind to. | Default `127.0.0.1`; set to `0.0.0.0` when using a reverse proxy. |
| `ECHO_JOURNAL_PORT` | Port to listen on. | Default `8000`. |
| `ECHO_JOURNAL_SSL_KEYFILE` | Path to TLS key file. | Used with `ECHO_JOURNAL_SSL_CERTFILE` to enable HTTPS. |
| `ECHO_JOURNAL_SSL_CERTFILE` | Path to TLS certificate. | Used with `ECHO_JOURNAL_SSL_KEYFILE` to enable HTTPS. |
| `BASIC_AUTH_USERNAME` | Username for optional HTTP Basic authentication. | |
| `BASIC_AUTH_PASSWORD` | Password for optional HTTP Basic authentication. | |

Set any of these variables in `settings.yaml` to tailor the app to your setup. Values provided via environment variables can override the defaults, but `settings.yaml` takes precedence. The **Settings** page lists current values and lets you edit them; changes are written to `settings.yaml` and take effect after restarting the server.
