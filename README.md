# Echo Journal

Minimalist, mobile-first journaling webapp designed for personal use with Docker, FastAPI, Markdown storage, and a warm minimalist UI.

## Features
- Responsive, mobile-first UI with dark mode support
- Warm minimalist aesthetic (Nunito + Merriweather fonts, gray-blue accents)
- Dynamic daily prompt from categorized `prompts.json` file
- Markdown entry storage (`/journals/YYYY-MM-DD.md`) on NAS via Docker volume
- No authentication, intended for secure local network (LAN) usage
- Backend implemented with FastAPI and Jinja2 templates

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
├── README.md
├── ROADMAP.md
└── LICENSE
```

## Setup instructions

1. **Prepare your environment**
   Ensure you have Docker and Docker Compose installed.

2. **NAS journal storage**
   The NAS location can be configured with the `JOURNALS_DIR` environment
   variable used in `docker-compose.yml`. Example:
   ```yaml
   volumes:
     - ${JOURNALS_DIR:-/mnt/nas/journals}:/journals
   ```

3. **Build and run**
   ```sh
   docker-compose up --build
   ```

4. **Access Echo Journal**
   Visit `http://localhost:8000` from any device on your LAN.

## Daily workflow
- Dynamic prompt rendered server-side via FastAPI + Jinja2 (`index.html`)
- Text area for daily entry
- Save writes entry as a Markdown file named after the date

## Additional notes
- Markdown files easily readable and portable
- Designed for ultra-low friction daily journaling: 
  - ≤ 5s load time target
  - ≤ 1s save time target
- Clean separation of UI, API, and storage logic

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


