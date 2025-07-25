# Echo Journal

Minimalist, mobile-first journaling webapp designed for personal use with Docker, FastAPI, Markdown storage, and a warm minimalist UI.

## Features
- Responsive, mobile-first UI with dark mode support
- Warm minimalist aesthetic (Nunito + Merriweather fonts, gray-blue accents)
- Dynamic daily prompt from categorized `prompts.json` file
- Markdown entry storage (`/journals/YYYY-MM-DD.md`) on NAS via Docker volume
- No authentication, intended for secure local network (LAN) usage
- Backend implemented with FastAPI and Jinja2 templates
- Archive view to browse past entries
- Settings page placeholder for future options

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

## Setup instructions

1. **Prepare your environment**
    Ensure you have Docker and Docker Compose installed. If you intend to run
    the application outside of Docker, Python 3.10 or newer is required.

2. **Journal storage path**
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

3. **Timezone**
   Adjust the timezone by editing the `TZ` variable in `docker-compose.yml`.

4. **Install frontend dependencies**
   Generate the Tailwind CSS by running:
   ```sh
   npm install
   npm run build:css
   ```
   This step is optional when building with Docker Compose, as the Dockerfile
   performs it automatically.

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

Defaults are suitable for Docker Compose but can be overridden when
running the app in other environments.

## Daily workflow
- Dynamic prompt rendered server-side via FastAPI + Jinja2 (`echo_journal.html`)
- Text area for daily entry
- Save writes entry as a Markdown file named after the date

## Additional notes
- Markdown files easily readable and portable
- Designed for ultra-low friction daily journaling:
  - ≤ 5s load time target
  - ≤ 1s save time target
- Clean separation of UI, API, and storage logic

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
- See [SECURITY.md](SECURITY.md) for instructions on reporting vulnerabilities.


