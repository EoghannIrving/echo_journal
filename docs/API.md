# Echo Journal API

The Echo Journal exposes a small REST API used by the web UI and CLI. All endpoints are relative to the server root (default `http://localhost:8510`).

## Endpoints

### GET /api/new_prompt
Return a journaling prompt.

Optional query params:

- `mood` – mood label such as `ok` or `sad`
- `energy` – energy level as an integer 1–4
- `style` – prompt category to filter (e.g., `memory`, `routines`)

```bash
curl 'http://localhost:8510/api/new_prompt?style=memory'
```

```json
{"prompt": "Describe a recent moment that made you smile.", "category": "Gratitude"}
```

### GET /api/ai_prompt
Generate a prompt using the OpenAI API when configured. Mood and energy query parameters are optional.

```bash
curl 'http://localhost:8510/api/ai_prompt?energy=3'
```

```json
{"prompt": "What energized you today?", "source": "openai"}
```

### GET /api/settings
Fetch current server settings.

```bash
curl http://localhost:8510/api/settings
```

```json
{"DATA_DIR": "/journals", "OPENAI_API_KEY": null, ...}
```

### POST /api/settings
Update settings and persist them to `settings.yaml`.

```bash
curl -X POST http://localhost:8510/api/settings \
     -H 'Content-Type: application/json' \
     -d '{"DATA_DIR": "/journals"}'
```

```json
{"status": "ok"}
```

### POST /api/backfill_songs
Re-scan existing entries for song and media metadata.

```bash
curl -X POST http://localhost:8510/api/backfill_songs
```

```json
{"songs_added": 0, "media_added": 0}
```

### POST /api/entry/{entry_date}/metadata
Re-fetch metadata for a single journal entry. Immich and Jellyfin integrations will be rerun when enabled, making it easy to add missing photos, songs, or media after the fact.

```bash
curl -X POST http://localhost:8510/api/entry/2023-08-01/metadata \
     -H 'Content-Type: application/json' \
     -H 'X-CSRF-Token: <token>'
```

```json
{"status": "success"}
```

### GET /api/reverse_geocode
Reverse geocode latitude and longitude using LocationIQ. Results are cached on disk.

```bash
curl "http://localhost:8510/api/reverse_geocode?lat=37.7749&lon=-122.4194"
```

```json
{"display_name": "San Francisco, California, United States", "city": "San Francisco", "region": "California", "country": "United States"}
```

### POST /api/reverse_geocode/invalidate
Invalidate the geocode cache for a specific coordinate or entirely when no coordinates are supplied.

```bash
curl -X POST "http://localhost:8510/api/reverse_geocode/invalidate?lat=37.7749&lon=-122.4194"
```

```json
{"status": "success"}
```
