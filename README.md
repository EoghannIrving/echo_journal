# Echo Journal Roadmap

## Phase 1: Core MVP ✅ Completed

- Mobile-first, minimalist web UI served locally via Docker  
- Single daily prompt from categorized static JSON pool  
- Markdown file storage directly on NAS via Docker volume mount  
- No authentication; LAN access only  
- Core UX goal: ≤ 5s load time, ≤ 1s save time  
- UI: warm, inviting, clean, text-only, dark mode support  

## Phase 2: Stickiness + Review Features ✅ Completed

- Archive/review view: week/month/year summaries (simple, minimalist)  
- UI polish: refined typography, spacing, subtle welcoming tone  
- Safeguard: prefill textarea if today's entry exists  
- Accessibility improvements (link contrast, footer legibility)  
- Dark mode texture consistency and polish  

## Phase 3: UX polish + Markdown support ✅ Completed

- **Markdown formatting toolbar (editor view): Completed**  
  - Inline helpers for `Bold`, `Italic`, `Heading`, `List`, `Quote`.  
  - Minimalist design, simple JS handlers.  
- **Markdown rendering for `/archive/<date>`: Completed**  
  - Server-side rendering with Python `markdown`.  
  - Styled output for consistent minimalist aesthetic and dark mode support.  
- **UI consistency audit: Completed**  
  - Typography, spacing, shadow depth, border radii harmonization.  
- **Animated letter-by-letter fade-in for `#welcome-message`: Completed**  
  - Smooth staggered reveal on `/` and `/archive/<date>`.  

## Phase 4: Archive + Stats foundation for enrichment ✅ Completed

- Expanded Archive view:  
  - Show metadata presence (📍location, 🌦️weather, 📷photo marker).  
  - Optional sorting/filtering by enrichment.  
- Stats dashboard: ✅ Completed  
  - Entry count by week/month/year.  
  - Word count stats.  
  - Optional "streaks" tracking (days/weeks with consecutive entries).  
- Metadata parsing improvements:  
  - Prepare archive backend to parse metadata consistently (frontmatter support if needed).  
  - Ensure clean fallback for legacy `.md` files.  
- Optional enrichment integration readiness:  
  - Immich (photos).  
  - Geolocation.  
  - Weather API.  

## Phase 5: Enrichment and polish (in progress)

### Backdated journaling support
- Allow user to create/edit entries for past dates  
- UI clearly shows: “You’re writing for {{date}}” (date banner)  
- Prompt uses past-tense framing (e.g., “Looking back…”)  
- Show contextual memory joggers:
  - Weather for that day  
  - Photos from Immich  
  - Songs or TV shows via Jellyfin/Last.fm  
  - Time clues (e.g., “You started your day with…”)  
- Fallback message if no metadata available  
- “Back to Today” link for easy return to current entry  

### Enrichment and UX Enhancements

- **Auto-generated prompt selection**  
  - Add What you watched (from Jellyfin) to the metadata
  - Uses contextual signals (Jellyfin, Immich, Last.fm, local time, weather)  
  - Backend rules or scoring engine selects from `prompts.json`  
  - Contextual input logged into `.meta.json` or frontmatter
  - AI-assisted prompts (“Need inspiration?” feature).  
  - Optional "New Prompt" link to gently refresh the daily suggestion if it doesn't resonate.  
    - Subtle secondary text that fades in on hover/tap.  
    - Client-side localStorage ensures the prompt stays consistent after saving.  
  - Optional secure remote access (auth, VPN/reverse proxy).  

- **Minimalist journal screen mode**  
  - One visible prompt only  
  - No toolbar or menus  
  - Prompt gently faded in for clarity  
  - Triggered by URL query or persistent setting  

- **Expanded 10-second journaling mode**  
  - No refresh or formatting  
  - Designed for raw, low-pressure reflection  
  - Auto-save on blur or idle timeout (optional)  

- **Full ambient metadata capture**  
  - Mood, time block, weather, Jellyfin/Last.fm/Immich content  
  - Files created: `.songs.json`, `.media.json`, `.photos.json`, `.meta.json`  
  - Example YAML frontmatter:
    ```yaml
    mood: Energized
    time_block: evening
    weather: Cloudy, 73°F
    songs_played: 4
    photos: 2
    tv: ["Doctor Who"]
    ```

- **Smart append-to-entry mode**  
  - Detects existing entry for the day  
  - Inserts separator (`---` or timestamp) for each append  
  - Preserves single-entry-per-day model  
  - “Add to Today’s Journal” button shown if applicable  
  - Metadata for each append saved to `.meta.json` as list  

## Phase 6: Insight, Patterning, and Personalization (planned)

- Filter archive view by mood, energy, tags  
- Mood/energy calendar view (heatmap style)  
- Personal time capsule: “Send to Future Me”  
  - Choose future date to show message  
- Prompt lane selector: Sensory | Reflective | Planning | Memory  
- Micro-nudge fallback for empty textarea  
  - Quote, image, or “Need a seed?” option  
- Export to PDF or memory cards  

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
| `category` | Prompt category selected when saving. | Stored for filtering and prompt history. |
| `photos` | List of photo objects from Immich, initially empty. | Adds a 📸 icon in the archive and shows thumbnails under the entry. |

Additional keys may be introduced in future integrations (e.g., facts, mood tracking). Unknown keys are ignored.

## Setup

Echo Journal runs as a small FastAPI application. Copy `.env.example` to
`.env` and edit paths or API keys before launching the server.

### Docker Compose quick start

```bash
docker-compose up --build
```

This builds the CSS and starts the app on <http://localhost:8510>.

### Running directly with Python

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   npm install
   npm run build:css
   ```

2. Launch the development server:

   ```bash
   uvicorn main:app --reload
   ```

### Environment variables

The `.env` file configures optional integrations and runtime paths:

- `JOURNALS_DIR` – host directory for your Markdown entries.
- `DATA_DIR`, `APP_DIR`, `PROMPTS_FILE`, `STATIC_DIR`, `TEMPLATES_DIR` –
  internal paths used by the application.
- `WORDNIK_API_KEY` – enables the Wordnik "word of the day" prompt.
- `IMMICH_URL` and `IMMICH_API_KEY` – fetch photos from your Immich server
  within the `IMMICH_TIME_BUFFER` hour window.
- `JELLYFIN_URL`, `JELLYFIN_API_KEY`, and `JELLYFIN_USER_ID` – pull
  recently watched shows from Jellyfin. `JELLYFIN_PAGE_SIZE` and
  `JELLYFIN_PLAY_THRESHOLD` control pagination and play percentage.
- Logging options: `LOG_LEVEL`, `LOG_FILE`, `LOG_MAX_BYTES`,
  `LOG_BACKUP_COUNT`.

Set any of these variables in `.env` or your environment to tailor the app to
your setup.
