# Echo Journal

*“A time capsule of a day in your life—anchored by how it felt, looked, sounded, and moved."*

Minimalist, mobile-first journaling webapp designed for personal use with Docker, FastAPI, Markdown storage, and a warm minimalist UI.
**Run Echo Journal only on a trusted local network (LAN). Do not expose it to the public internet.**

## Quickstart

1. Copy `.env.example` to `.env`.
2. Start the app with Docker:

   ```sh
   docker-compose up --build
   ```

   Or run locally with Python 3.10+:

   ```sh
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

3. If you're not using Docker, **you must** build the CSS assets first:

   ```sh
   npm install && npm run build:css
   ```

   Docker users can skip this step—the Dockerfile already installs dependencies
   and builds the CSS during the image build.

See the [Setup instructions](#setup-instructions) section below for full details.

## Features
- Responsive, mobile-first UI with dark mode support
- Warm minimalist aesthetic (Nunito + Merriweather fonts, gray-blue accents)
- Dynamic daily prompt from categorized `prompts.json` file
- Markdown entry storage (`/journals/YYYY-MM-DD.md`) on NAS via Docker volume
- No authentication, intended for secure local network (LAN) usage
- Backend implemented with FastAPI and Jinja2 templates
- Archive view to browse past entries
- Settings page placeholder for future options
- Stats dashboard showing entry counts, word totals and streaks
- Optional metadata saved with each entry, including location, weather,
  time of day and the Word of the Day. Photo and song metadata can also
  be captured when Immich or Jellyfin are configured.

## Project structure
```
.
├── BUGS.md
├── Dockerfile
├── docker-compose.yml
├── main.py
├── prompts.json
├── requirements.txt
├── static
│   ├── style.css
│   ├── icons/
│   └── textures/
├── templates
│   ├── archives.html
│   ├── base.html
│   └── echo_journal.html
├── tests
│   └── test_endpoints.py
├── README.md
├── ROADMAP.md
└── LICENSE
```
See [BUGS.md](BUGS.md) for the list of known issues.

## Setup instructions

1. **Prepare your environment**
    Ensure you have Docker and Docker Compose installed. If you intend to run
    the application outside of Docker, Python 3.10 or newer is required.

2. **Create a .env file**
   Copy `.env.example` to `.env` and fill in any variables you wish to set.

3. **Journal storage path**
   When using Docker Compose, set the `JOURNALS_DIR` environment variable
   to control the host path that is mounted to `/journals` inside the
   container:
   ```yaml
   volumes:
     - ${JOURNALS_DIR:-/mnt/nas/journals}:/journals
   ```
   If you run the application without Docker, or need to override the
   location inside the container, set the `DATA_DIR` environment variable
   to the desired path before starting the app.

4. **Timezone**
   Adjust the timezone by editing the `TZ` variable in `docker-compose.yml`.

5. **Install frontend dependencies**
   For local development you need to generate the Tailwind CSS:
   ```sh
   npm install && npm run build:css
   ```
   Docker users do not need this step—the Dockerfile automatically installs
   dependencies and builds the CSS during the image build.

5. **Build and run**
   ```sh
   docker-compose up --build
   ```

6. **Access Echo Journal**
   Visit `http://localhost:8510` from any device on your LAN.

## Environment variables

The application looks for the following optional variables:

- `DATA_DIR` – path used to store journal Markdown files
- `APP_DIR` – base directory for static assets and templates
- `PROMPTS_FILE` – location of the prompts JSON file
- `STATIC_DIR` – directory for static files served under `/static`
- `TEMPLATES_DIR` – directory containing Jinja2 templates
- `WORDNIK_API_KEY` – API key used to fetch the Wordnik word of the day
- `IMMICH_URL` – base URL of your Immich API endpoint (for example `http://immich.local/api`)
- `IMMICH_API_KEY` – API key used to authorize requests to Immich
- `IMMICH_TIME_BUFFER` – hours to extend photo searches before and after each date (default `15`)
- `JELLYFIN_URL` – base URL of your Jellyfin server (for example `http://jellyfin.local:8096`)
- `JELLYFIN_API_KEY` – optional API key for Jellyfin requests
- `JELLYFIN_USER_ID` – Jellyfin user ID whose play history is queried
- `JELLYFIN_PAGE_SIZE` – items to fetch per request when querying plays (default `200`)
- `JELLYFIN_PLAY_THRESHOLD` – minimum percent played for a song to count (default `90`)
- `LOG_LEVEL` – logging verbosity (default `DEBUG`)
- `LOG_FILE` – path for the log file (default `DATA_DIR/echo_journal.log`)
- `LOG_MAX_BYTES` – rotate the log after this many bytes (default `1048576`)
- `LOG_BACKUP_COUNT` – number of rotated log files to keep (default `3`)

Defaults are suitable for Docker Compose but can be overridden when
running the app in other environments.

### Immich API setup

To enable photo metadata from [Immich](https://github.com/immich-app/immich),
create an access token in your Immich account and set the two variables above.
For a Docker Compose install, add them under the service's `environment` block:

```yaml
environment:
  - IMMICH_URL=http://immich.local/api
  - IMMICH_API_KEY=your_generated_token
  # Optional: widen date searches by this many hours on either side
  - IMMICH_TIME_BUFFER=15
```

With these configured, saving **or viewing** an entry will fetch any photos
from Immich that match the entry's date and store a companion JSON file
alongside the Markdown entry.
The interactions with Immich are logged using the `ej.immich` logger so you can
see when requests are made and JSON files written.

### Jellyfin API setup

To record your most-listened songs for each day, create an API key in your
Jellyfin account and determine your user ID. Add the variables below to the
Compose file or `.env`:

```yaml
environment:
  - JELLYFIN_URL=http://jellyfin.local:8096
  - JELLYFIN_API_KEY=your_token
  - JELLYFIN_USER_ID=abcdef123456
  - JELLYFIN_PAGE_SIZE=200
  - JELLYFIN_PLAY_THRESHOLD=90
```

When enabled, saving an entry writes a `<date>.songs.json` file listing up to
twenty songs you played that day. Requests are logged with the `ej.jellyfin`
logger.
Existing journals can be retroactively populated using the `/api/backfill_songs`
endpoint.

## Daily workflow
- Dynamic prompt rendered server-side via FastAPI + Jinja2 (`echo_journal.html`)
- Text area for daily entry
- Save writes entry as a Markdown file named after the date

## Archive
The `/archive` page lists past entries grouped by month.

Query parameters:
- `sort_by` – ordering of entries: `date` (default), `location`, `weather`, or `photos`.
- `filter` – limit results to entries containing metadata. Use `has_location`, `has_weather`, or `has_photos`.

Example: `/archive?sort_by=location&filter=has_location`.

## Stats
Visit `/stats` to see aggregated entry information including counts by week,
month and year, total word counts and your current/longest streaks.

## Additional notes
- Markdown files easily readable and portable
- Each entry is stored as Markdown with a small YAML frontmatter block storing
  metadata such as location, weather, save time, photos and the Word of the Day
- Designed for ultra-low friction daily journaling:
  - ≤ 5s load time target
  - ≤ 1s save time target
- Clean separation of UI, API, and storage logic
- Optional Immich photo integration via `IMMICH_URL` and `IMMICH_API_KEY` environment variables
- Optional Jellyfin track logging via `JELLYFIN_URL` and related variables
- Client-side geolocation calls `/api/reverse_geocode` to label coordinates

## Monitoring request timings

Each response includes an `X-Response-Time` header showing how long the request
took. You can also visit the `/metrics` endpoint to see a JSON list of recent
paths and their durations.

## Security considerations

Echo Journal intentionally does not implement any authentication. It is designed
for use on a trusted local network where access to the web interface is
restricted by your network environment. Running the application directly on the
public internet is **not recommended**.

If you need to deploy publicly, consider one of the following approaches:

- Add your own authentication layer using FastAPI's dependency system or a
  third-party provider.
- Place the app behind a secure reverse proxy (such as Nginx or Caddy) that
  handles HTTPS and access control.
For instructions on reporting security vulnerabilities, see [SECURITY.md](SECURITY.md).

## Contributing

Pull requests are welcome! Before opening one, please run `black`, `pylint` and
`pytest` locally to make sure the codebase stays clean and all tests pass. One
way to do this is:

```sh
black .
pylint $(git ls-files '*.py') --fail-under=8
pytest
```

Running the test suite should report `47 passed` along with a few warnings:

```
47 passed, 24 warnings in 2.0s
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

Known issues are tracked in [BUGS.md](BUGS.md).



