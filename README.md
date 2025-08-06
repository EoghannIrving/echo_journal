# Echo Journal

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE) [![CI](https://github.com/EoghannIrving/echo_journal/actions/workflows/pytest.yml/badge.svg)](https://github.com/EoghannIrving/echo_journal/actions/workflows/pytest.yml) ![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue) ![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-blue)

Echo Journal is a minimalist FastAPI journaling app that stores Markdown
entries enriched with optional metadata like mood, energy, location, weather,
photos and media. Daily prompts can be refreshed or even generated on demand
with an AI helper. Below is the project roadmap and current feature set.

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration) ([details](docs/configuration.md))
- [Security considerations](#security-considerations)
- [CLI commands](#cli-commands)
- [API reference](#api-reference)

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

### Automated setup

```bash
git clone https://github.com/EoghannIrving/echo_journal.git
cd echo_journal
./scripts/setup.sh
```

The `setup.sh` script creates a `.venv`, installs Python dependencies, runs `npm install`, and builds the Tailwind CSS bundle.

### Manual setup

```bash
git clone https://github.com/EoghannIrving/echo_journal.git
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

## Configuration

Echo Journal reads options from `<DATA_DIR>/.settings/settings.yaml` (default
`/journals/.settings/settings.yaml`). If the file is missing, environment
variables are used instead. Copy the example file to get started:

```bash
cp settings.example.yaml settings.yaml
# edit settings.yaml to set DATA_DIR, APP_DIR, and API keys
```

See [docs/configuration.md](docs/configuration.md) for a full list of
configuration values and defaults.

## Example walkthrough

To verify the app runs, try the following sequence:

```bash
git clone https://github.com/EoghannIrving/echo_journal.git
cd echo_journal
python -m venv .venv && source .venv/bin/activate
pip install .  # installs Echo Journal and its Python dependencies
uvicorn echo_journal.main:app --reload
# or
echo-journal
```

Then open <http://localhost:8510> in your browser. You should see the Echo Journal interface and can create a test entry.

## API reference

See [docs/API.md](docs/API.md) for a full list of available endpoints.

## CLI commands

`echo-journal` starts the application using Uvicorn.

```bash
echo-journal
```

Set environment variables to change host, port, or enable TLS:

```bash
ECHO_JOURNAL_HOST=0.0.0.0 ECHO_JOURNAL_PORT=8510 echo-journal
ECHO_JOURNAL_SSL_KEYFILE=path/to/key.pem ECHO_JOURNAL_SSL_CERTFILE=path/to/cert.pem echo-journal
```

For development with auto reload:

```bash
uvicorn echo_journal.main:app --reload
```

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

Details about the entry front matter and energy level mapping have moved to [docs/frontmatter.md](docs/frontmatter.md).

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

## Testing

Run the test suite with:

```bash
pytest
```

## Bugs and Issues

Known issues are tracked in [BUGS.md](BUGS.md). If you run into a problem that's not listed there, please follow the guidance in that file to file a bug report or open a GitHub issue.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to get started.

## License

Echo Journal is released under the [GNU General Public License v3](LICENSE).
By contributing, you agree that your contributions will be licensed under the same terms.
