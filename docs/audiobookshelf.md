# AudioBookShelf Integration

Required permissions: API token with access to user playback data (`/api/me`) and item metadata (`/api/items/<id>`). For podcasts, episode access (`/api/podcasts/episodes/<id>`) is used when available.

Configuration options:
- `AUDIOBOOKSHELF_URL`: Base URL to the server
- `AUDIOBOOKSHELF_API_TOKEN`: Bearer token for API calls
- `INTEGRATION_AUDIOBOOKSHELF`: Toggle integration on/off
- `AUDIOBOOKSHELF_POLL_ENABLED`: Enable background polling loop
- `AUDIOBOOKSHELF_POLL_INTERVAL_SECONDS`: Interval for polling in seconds

Data schema and storage:
- Daily records saved to `<DATA_DIR>/.meta/<date>.audio.json`
- Each record includes identifiers (`abs_library_item_id`, `abs_episode_id`) and metadata (title, author, narrator, publisher, series), plus playback fields (`duration`, `progress`, `current_time`, `is_finished`, `last_update`)
- Frontmatter indicator `audio` is populated for archive filtering

Synchronization and consistency:
- Metadata is fetched on save, on archive view, and via the `/api/entry/{date}/metadata` refresh endpoint
- Optional background poller checks today’s entry and updates audio JSON regularly
- Incremental updates overwrite the JSON atomically per run; downstream consumers read the entire list

Error handling:
- Network and HTTP errors are logged and ignored for non-blocking UX
- Missing or malformed fields are skipped
- Authentication failures (missing/invalid token) disable activity fetch silently

Data retention:
- Audio JSON files are stored alongside journal entries under `.meta` and follow entry lifecycle
- To remove, delete the corresponding `.audio.json` file

Troubleshooting:
- Verify token and URL via `curl -H "Authorization: Bearer <token>" <URL>/api/me`
- Check application logs under `<DATA_DIR>/.logs/echo_journal.log` for `ej.audiobookshelf`
- Ensure `INTEGRATION_AUDIOBOOKSHELF` is set to `true` in `settings.yaml`
