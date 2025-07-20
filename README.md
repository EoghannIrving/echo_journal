# Echo Journal

Minimalist, mobile-first journaling webapp designed for personal use with Docker, FastAPI, Markdown storage, and a warm minimalist UI.

## Features
- Responsive, mobile-first UI with dark mode support
- Warm minimalist aesthetic (Nunito + Merriweather fonts, gray-blue accents)
- Dynamic daily prompt from categorized `prompts.json` file
- Markdown entry storage (`/journals/YYYY/YYYY-MM-DD.md`) on NAS via Docker volume
- No authentication, intended for secure local network (LAN) usage
- Backend implemented with FastAPI and Jinja2 templates

## Project structure
```
.
├── Dockerfile
├── docker-compose.yml
├── main.py
├── requirements.txt
├── prompts.json
├── static
│   ├── echo_journal.html
│   └── style.css
├── templates
│   └── index.html  # (optional for Jinja2 template rendering)
├── README.md
├── ROADMAP.md
└── VALIDATION.md
```

## Setup instructions

1. **Prepare your environment**
   Ensure you have Docker and Docker Compose installed.

2. **NAS journal storage**
   Adjust `docker-compose.yml` if your NAS path differs. Example:
   ```yaml
   volumes:
     - /mnt/nas/journals:/journals
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
- Save writes entry as Markdown file organized by year and date

## Additional notes
- Markdown files easily readable and portable
- Designed for ultra-low friction daily journaling: 
  - ≤ 5s load time target
  - ≤ 1s save time target
- Clean separation of UI, API, and storage logic

