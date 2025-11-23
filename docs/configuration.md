# Configuration

On startup the application looks for a `settings.yaml` file in `<DATA_DIR>/.settings/settings.yaml` (default `/journals/.settings/settings.yaml`). This location can be overridden with the `SETTINGS_PATH` environment variable. If it is missing a warning is logged noting the expected path and the app falls back to environment variables. The `settings.yaml` file configures optional integrations and runtime paths. It is the authoritative source for these values:

| Variable | Purpose | Notes / Defaults |
| --- | --- | --- |
| `DATA_DIR` | Internal application path. | Default `/journals`. |
| `APP_DIR` | Internal application directory. | Automatically derived from the installed package; override with `APP_DIR` env var if needed. |
| `PROMPTS_FILE` | Location of YAML prompts file. | Default `<APP_DIR>/prompts.yaml`. |
| `STATIC_DIR` | Directory for static assets. | Default `<APP_DIR>/static`. |
| `TEMPLATES_DIR` | Directory for Jinja2 templates. | Default `<APP_DIR>/templates`. |
| `SETTINGS_PATH` | Full path to the settings.yaml file. | Default `<DATA_DIR>/.settings/settings.yaml`. |
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
| `NOMINATIM_USER_AGENT` | Legacy user agent for Nominatim requests. | Still used by older clients; safe to leave default. |
| `LOCATIONIQ_API_KEY` | Enables reverse geocoding via LocationIQ. | Required for `/api/reverse_geocode`. |
| `GEO_CACHE_PATH` | Disk path of the geocode cache file. | Default `<DATA_DIR>/.cache/reverse_geocode.json`. |
| `GEO_CACHE_TTL_SECONDS` | Cache entry expiration in seconds. | Default `86400` (24 hours). |
| `GEO_CACHE_MAX_ENTRIES` | Maximum number of cached entries. | Default `1000`. |
| `INTEGRATION_LOCATION` | Include geolocation data in entry frontmatter. | Default `true`. |
| `INTEGRATION_WEATHER` | Include current weather in entry frontmatter. | Default `true`. |
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
| `ECHO_JOURNAL_ENV_PATH` | Path to the .env file read by helper utilities. | Default `<APP_DIR>/../.env`. |
| `AUDIOBOOKSHELF_URL` | Base URL to AudioBookShelf server. | Example `http://abs:13378`. |
| `AUDIOBOOKSHELF_API_TOKEN` | API token for AudioBookShelf. | Used as `Authorization: Bearer <token>`. |
| `INTEGRATION_AUDIOBOOKSHELF` | Enable AudioBookShelf metadata sync. | Defaults to `true`. |
| `AUDIOBOOKSHELF_POLL_ENABLED` | Enable background polling for playback. | Defaults to `false`. |
| `AUDIOBOOKSHELF_POLL_INTERVAL_SECONDS` | Poll interval for playback sync. | Defaults to `600`. |

Set any of these variables in `settings.yaml` to tailor the app to your setup. Values provided via environment variables can override the defaults, but `settings.yaml` takes precedence. The **Settings** page lists current values and lets you edit them; changes are written to `settings.yaml` and take effect after restarting the server.
