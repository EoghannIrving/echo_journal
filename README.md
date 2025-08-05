# Echo Journal

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE) [![CI](https://github.com/OWNER/echo_journal/actions/workflows/pytest.yml/badge.svg)](https://github.com/OWNER/echo_journal/actions/workflows/pytest.yml) ![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue) ![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-blue)

Echo Journal is a minimalist FastAPI journaling app that stores Markdown
entries enriched with optional metadata like mood, energy, location, weather,
photos and media. Daily prompts can be refreshed or even generated on demand
with an AI helper. Below is the project roadmap and current feature set.

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Security considerations](#security-considerations)

## Features

- Markdown entries saved locally as `.md` files
- Optional metadata for mood, energy, location, weather, photos, and media
- Daily prompts from `prompts.yaml` with AI assistance and a “New Prompt” refresh
- Archive view and stats dashboard for reviewing past entries
- Per-browser toggles for Wordnik, Immich, and Jellyfin integrations
- Optional HTTP Basic authentication for remote access

## Prerequisites

- **Python** 3.10+
- *(Optional)* **Node.js** 18+ and npm if you plan to modify Tailwind CSS. A prebuilt `static/tailwind.css` is included for immediate use.
- **Docker** and **Docker Compose** (optional, for containerized deployment). If the `docker compose` command is unavailable, install the [Docker Compose plugin](https://docs.docker.com/compose/install/).

## Installation

### Clone and install dependencies

```bash
git clone https://github.com/<your_user>/echo_journal.git
cd echo_journal
python -m venv .venv && source .venv/bin/activate
pip install .  # installs Echo Journal and its Python dependencies
```

The repository bundles a compiled `static/tailwind.css`, so Node.js and npm are only needed if you want to change styles. Running `npm install` will automatically rebuild the CSS via the `postinstall` script.

Python dependencies are defined in `pyproject.toml` and installed with `pip install .`.

## Usage

### Run with Python

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install .
   # npm install  # only needed if modifying Tailwind styles
   ```

2. Start the development server:

   ```bash
   uvicorn echo_journal.main:app --reload
   # or use the console script
   echo-journal
   ```

### Run with Docker Compose

> Note: The following commands use Docker Compose v2. If `docker compose` is unavailable, install the [Docker Compose plugin](https://docs.docker.com/compose/install/).

1. **Copy the example environment file and adjust settings as needed:**

   ```bash
   cp .env.example .env
   # edit .env to change HOST_PORT, DATA_DIR, or TLS paths
   ```

2. **Prepare a persistent journals directory (matches `DATA_DIR`, default `data`):**

   ```bash
   mkdir -p data
   ```

3. **Start the container:**

   ```bash
   docker compose up --build
   ```

   Then open <http://localhost:8510> (or your chosen `HOST_PORT`) in your browser.

4. **Stop the container while preserving data:**

   ```bash
   docker compose down
   ```

   Journal files remain in the mounted `data` directory on the host.

## Example walkthrough

To verify the app runs, try the following sequence:

```bash
git clone https://github.com/<your_user>/echo_journal.git
cd echo_journal
python -m venv .venv && source .venv/bin/activate
pip install .  # installs Echo Journal and its Python dependencies
uvicorn echo_journal.main:app --reload
# or
echo-journal
```

Then open <http://localhost:8510> in your browser. You should see the Echo Journal interface and can create a test entry.

## API and CLI reference

### API endpoints

These endpoints power the web UI. For a complete list see the FastAPI app in
[`src/echo_journal/main.py`](src/echo_journal/main.py). *TODO: expand into a
dedicated API guide.*

- `GET /api/new_prompt` – return a journaling prompt.
  ```bash
  curl http://localhost:8510/api/new_prompt
  ```
  ```json
  {"prompt": "Describe a recent moment that made you smile.", "category": "Gratitude"}
  ```

- `GET /api/ai_prompt?energy=3` – generate a prompt using the OpenAI API when
  configured. Mood and energy parameters are optional; if omitted, the service defaults to a gentle "soft" anchor.
  ```bash
  curl 'http://localhost:8510/api/ai_prompt?energy=3'
  ```
  ```json
  {"prompt": "What energized you today?", "source": "openai"}
  ```

- `GET /api/settings` – fetch current server settings.
  ```bash
  curl http://localhost:8510/api/settings
  ```
  ```json
  {"DATA_DIR": "/journals", "OPENAI_API_KEY": null, ...}
  ```

- `POST /api/settings` – update settings and persist them to `settings.yaml`.
  ```bash
  curl -X POST http://localhost:8510/api/settings \
       -H 'Content-Type: application/json' \
       -d '{"DATA_DIR": "/journals"}'
  ```
  ```json
  {"status": "ok"}
  ```

- `POST /api/backfill_songs` – re-scan existing entries for song and media
  metadata.
  ```bash
  curl -X POST http://localhost:8510/api/backfill_songs
  ```
  ```json
  {"songs_added": 0, "media_added": 0}
  ```

### CLI commands

- `echo-journal` – start the application using Uvicorn.
  ```bash
  echo-journal
  ```

- `uvicorn echo_journal.main:app --reload` – run the development server with
  auto reload.

*TODO: flesh out CLI documentation as new commands are introduced.*

## Testing

Run the test suite to verify your setup:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
pytest
```

If you modify `tailwind_src.css`, run `npm install` to rebuild `static/tailwind.css` (the postinstall script handles the build).

## Roadmap

Echo Journal's development roadmap is maintained in [ROADMAP.md](ROADMAP.md). Highlights:

- **Phases 1–4**: Core MVP, review tools, and archive/stats features – *Completed*
- **Phase 5**: Enrichment and polish – *In progress*
- **Phase 6**: Insight, patterning, and personalization – *Planned*

## Design Guardrails

- Prioritize warmth and ultra-low friction  
- Markdown format for longevity and openness  
- Support single-action journaling: open → type → save  
- Clear UI/API separation using FastAPI + Jinja2

## YAML Frontmatter Reference

Each journal entry begins with a YAML block. These fields are parsed whenever an entry is saved or displayed.

### Example

```yaml
location: Example Place
weather: 18°C code 1
save_time: Evening
wotd: luminous
wotd_def: emitting light
category: Gratitude
photos: []
```

### Field details

| Field | Purpose | Application usage |
| ----- | ------- | ----------------- |
| `location` | Human readable label from browser geolocation. | Shown with a 📍 icon in archive and entry views. |
| `weather` | Temperature and weather code from Open‑Meteo. | Parsed by `format_weather` to show an icon; codes are mapped to words for mouseover titles. |
| `save_time` | Morning/Afternoon/Evening/Night recorded at save time. | Provides context for when the entry was written. |
| `wotd` | Wordnik word of the day. | Displayed in the entry sidebar and as an icon in the archive list. |
| `wotd_def` | Definition for the word of the day. | Shown alongside the word in entry views. |
| `category` | Prompt category selected when saving. | Stored for filtering and prompt history. |
| `photos` | List of photo objects from Immich, initially empty. | Adds a 📸 icon in the archive and shows thumbnails under the entry. |

Additional keys may be introduced in future integrations (e.g., facts, mood tracking). Unknown keys are ignored.

## Energy level mapping

Energy selections from the UI are translated to integers before hitting `/api/new_prompt`.
This allows the backend to score prompts based on numeric intensity.

| Energy | Value |
| ------ | ----- |
| `drained` | 1 |
| `low` | 2 |
| `ok` | 3 |
| `energized` | 4 |

### Configuration

On startup the application looks for a `settings.yaml` file in
`<DATA_DIR>/.settings/settings.yaml` (default `/journals/.settings/settings.yaml`). If it is
missing a warning is logged noting the expected path and the app falls back to
environment variables. The `settings.yaml` file configures optional
integrations and runtime paths. It is the authoritative source for these
values:

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

Set any of these variables in `settings.yaml` to tailor the app to your setup.
Values provided via environment variables can override the defaults, but
`settings.yaml` takes precedence. The **Settings** page lists current values
and lets you edit them; changes are written to `settings.yaml` and take effect
after restarting the server.

### Disabling integrations

The web UI includes a **Settings** page where optional integrations can be
toggled per browser. Uncheck Wordnik, Immich, or Jellyfin integrations to
disable their metadata. A future "Fact of the Day" option will also be
toggleable here once implemented. Your choices are stored in `localStorage` and
the server skips fetching data for any disabled integrations when building
frontmatter.

### Security considerations

- Set `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` before exposing the app
  to the internet. Without these variables, anyone can access your journal.
- Provide a valid contact email in `NOMINATIM_USER_AGENT` to comply with the
  Nominatim usage policy; requests without contact info may be throttled or
  rejected.
- The `/api/settings` endpoint returns server configuration details for
  convenience during development. Restrict it to trusted networks or run the
  app behind a VPN or reverse proxy to avoid leaking secrets.
- Outbound requests now include a 10-second timeout and prompt categories are
  sanitized before saving or rendering, limiting the impact of malicious or
  unexpected input.

### Serving behind a VPN or reverse proxy

Echo Journal binds to `127.0.0.1` by default so it's only reachable from the
local machine. To make it available elsewhere, run it behind your VPN
(e.g. WireGuard) or a reverse proxy such as Nginx or Caddy. The proxy can handle
TLS termination and restrict access to known networks. Set
`ECHO_JOURNAL_HOST=0.0.0.0` if the proxy needs to reach the app over the
network.

Example Nginx configuration terminating TLS and proxying requests:

```nginx
server {
    listen 443 ssl;
    server_name journal.example.com;

    ssl_certificate     /etc/letsencrypt/live/journal.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/journal.example.com/privkey.pem;

    location / {
       proxy_pass http://127.0.0.1:8510;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

When exposing the app publicly, enable Basic Auth by setting
`BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` so unauthenticated requests are
rejected with a `401` response.

## Bugs and Issues

Known issues are tracked in [BUGS.md](BUGS.md). If you run into a problem that's not listed there, please follow the guidance in that file to file a bug report or open a GitHub issue.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to get started.

## License

Echo Journal is released under the [GNU General Public License v3](LICENSE).
By contributing, you agree that your contributions will be licensed under the same terms.
