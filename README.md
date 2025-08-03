# Echo Journal

Echo Journal is a minimalist FastAPI journaling app that stores Markdown
entries enriched with optional metadata like mood, energy, location, weather,
photos and media. Daily prompts can be refreshed or even generated on demand
with an AI helper. Below is the project roadmap and current feature set.

## Prerequisites

- **Python** 3.10+
- **Node.js** 18+ and npm for building Tailwind CSS assets
- **Docker** and **Docker Compose** (optional, for containerized deployment)

## Installation

### Clone and install dependencies

```bash
git clone https://github.com/<your_user>/echo_journal.git
cd echo_journal
python -m venv .venv && source .venv/bin/activate
pip install .  # installs Echo Journal and its Python dependencies
npm install
npm run build:css
```

Python dependencies are defined in `pyproject.toml` and installed with `pip install .`.

## Usage

### Run with Python

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install .
   npm install
   npm run build:css
   ```

2. Copy the example environment file and set `JOURNALS_DIR` and any other needed variables:

   ```bash
   cp .env.example .env
   # edit .env to point JOURNALS_DIR to a writable path
   ```

3. Start the development server:

   ```bash
   uvicorn echo_journal.main:app --reload
   # or use the console script
   echo-journal
   ```

### Run with Docker Compose

```bash
cp .env.example .env
# adjust JOURNALS_DIR and other variables in .env
docker-compose up --build
```

## Example walkthrough

To verify the app runs, try the following sequence:

```bash
git clone https://github.com/<your_user>/echo_journal.git
cd echo_journal
python -m venv .venv && source .venv/bin/activate
pip install .  # installs Echo Journal and its Python dependencies
npm install
npm run build:css
cp .env.example .env  # set JOURNALS_DIR inside
uvicorn echo_journal.main:app --reload
# or
echo-journal
```

Then open <http://localhost:8000> in your browser. You should see the Echo Journal interface and can create a test entry.

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
| `weather` | Temperature and weather code from Open‑Meteo. | Parsed by `format_weather` to show an icon and temperature. |
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

## Setup

Echo Journal runs as a small FastAPI application. Create a `settings.yaml`
file and edit paths or API keys before launching the server. This file is the
authoritative source for configuration.

### Docker Compose quick start

```bash
docker-compose up --build
```

This builds the CSS and starts the app on <http://localhost:8510>.

The container defaults to UTC. To use your local timezone, set the
`TZ` environment variable before starting:

```bash
TZ=America/Los_Angeles docker-compose up --build
```

You can also set `TZ=Your/Timezone` in `settings.yaml`. Restart the server for
changes to take effect.

### Running directly with Python

1. Install dependencies:

   ```bash
   pip install .
   # installs Echo Journal and its Python dependencies
   npm install
   npm run build:css
   ```

2. Launch the development server:

   ```bash
   uvicorn echo_journal.main:app --reload
   # or
   echo-journal
   ```

### Environment variables

The `settings.yaml` file configures optional integrations and runtime paths. It
is the authoritative source for these values:

- `JOURNALS_DIR` – host directory for your Markdown entries.
- `DATA_DIR`, `APP_DIR`, `PROMPTS_FILE`, `STATIC_DIR`, `TEMPLATES_DIR` –
  internal paths used by the application.
- `WORDNIK_API_KEY` – enables the Wordnik "word of the day" prompt.
- `OPENAI_API_KEY` – enables AI-generated prompts via the OpenAI API.
  Usage may incur costs and is subject to OpenAI's rate limits.
- `IMMICH_URL` and `IMMICH_API_KEY` – fetch photos from your Immich server
  within the `IMMICH_TIME_BUFFER` hour window.
- `JELLYFIN_URL`, `JELLYFIN_API_KEY`, and `JELLYFIN_USER_ID` – pull
  recently watched shows from Jellyfin. `JELLYFIN_PAGE_SIZE` and
  `JELLYFIN_PLAY_THRESHOLD` control pagination and play percentage.
- `NOMINATIM_USER_AGENT` – identifies your app when calling the Nominatim
  reverse geocoding API. Include contact info per the usage policy.
- Logging options: `LOG_LEVEL`, `LOG_FILE`, `LOG_MAX_BYTES`,
  `LOG_BACKUP_COUNT`.
- `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` – enable optional HTTP Basic
  authentication for the web UI. When both are set, all requests must include a
  matching `Authorization` header.

Set any of these variables in `settings.yaml` or your environment to tailor the
app to your setup. The **Settings** page lists current values and lets you edit
them; changes are written to `settings.yaml` and take effect after restarting
the server.

### Google Cloud service account credentials

Some integrations require a Google Cloud service account. Provide the full JSON
key downloaded from the Google Cloud console; it must include top-level fields
like `type`, `client_email`, `token_uri`, and `private_key`. Keys that only
contain a `"web"` section are OAuth client configs and will not work.

```json
{
  "type": "service_account",
  "project_id": "my-project",
  "private_key_id": "abc123",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "my-service-account@my-project.iam.gserviceaccount.com",
  "client_id": "1234567890",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

Set the path to this file before running the app:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

You can also set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json`
in `settings.yaml`. Restart the server after updating the file.

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

For secure remote access, run Echo Journal behind your VPN (e.g. WireGuard) or a
reverse proxy such as Nginx or Caddy. The proxy can handle TLS termination and
restrict access to known networks. When exposing the app publicly, enable Basic
Auth by setting `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` so unauthenticated
requests are rejected with a `401` response.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to get started.

## License

Echo Journal is released under the [GNU General Public License v3](LICENSE).
By contributing, you agree that your contributions will be licensed under the same terms.
