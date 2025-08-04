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
- Optional enrichment integration readiness ✅ Completed
  - Immich (photos)
  - Geolocation
  - Weather API

## Phase 5: Enrichment and polish (in progress)
- Document YAML frontmatter structure in the README ✅ Completed
- Add optional "Fact of the Day" integration
- Provide an AI-assisted prompt helper ✅ Completed
- Allow refreshing the prompt via a "New Prompt" link ✅ Completed
- Evaluate secure remote access options and toggles for integrations ✅ Completed


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
- Gentle restart reminder if yesterday's entry is missing ✅
- **Auto-generated prompt selection**
  - Add What you watched (from Jellyfin) to the metadata ✅
  - Uses contextual signals (Jellyfin, Immich, Last.fm, local time, weather)
  - Backend rules or scoring engine selects from `prompts.yaml`
  - Contextual input logged into `.meta.json` or frontmatter
  - AI-assisted prompts (“Need inspiration?” feature) ✅
  - Optional "New Prompt" link to gently refresh the daily suggestion if it doesn't resonate ✅
    - Subtle secondary text that fades in on hover/tap.
    - Client-side localStorage ensures the prompt stays consistent after saving. ✅
  - Optional secure remote access (auth, VPN/reverse proxy) ✅
- **Minimalist journal screen mode** ✅
  - One visible prompt only ✅
  - No toolbar or menus ✅
  - Prompt gently faded in for clarity✅
  - Triggered by URL query or persistent setting
- **Expanded 10-second journaling mode**
  - No refresh or formatting
  - Designed for raw, low-pressure reflection
  - Auto-save on blur or idle timeout (optional)
- **Full ambient metadata capture** ✅
  - Mood, time block, weather, Jellyfin/Last.fm/Immich content ✅
  - Files created under `.meta/`: `<date>.songs.json`, `<date>.media.json`, `<date>.photos.json`, `<date>.meta.json`✅
  - Example YAML frontmatter: ✅
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

### AuADHD Support Enhancements
- Mood + energy tagging (stored client-side) ✅
  - UI toggle with emoji **and** visible text labels ✅
  - Example: 😔 Sad · 😐 Meh · 😊 Okay · 😍 Joyful · 🧠 Focused · ⚡ Energized · 🪫 Drained ✅
  - Optional text-only mode (toggleable via localStorage or user settings)
  - Optional dropdown UI for accessibility ✅
- Prompt strategy matched to mood/energy✅
  - Use categorized prompt sets (gentle, sensory, contrast, etc.) ✅
  - Add "Prompt Style" dropdown or auto-match by tag
- 10-second journaling mode
  - Minimal UI for 1–3 word entries, emoji, or tags
  - Saves stub with timestamp and optional metadata
- Time-contextual prompt variations
  - Add frames like “This morning…”, “Looking back…”, “To Future You…”
- Quick tag reactions ✅
  - Visual + textual buttons: e.g., 😔 Sad, ⚡ Energized, 🪫 Drained ✅
  - Enable archive filtering and stats
- Streak disruption softness ✅ Completed
  - If no entry exists for yesterday, show gentle “Restart from today?” message ✅
  - Avoid shaming or pressure ✅
- Prompt explanation tooltips
  - Optional: hover or tap to explain what kind of prompts each mood receives

### Jellyfin Viewing Integration
- Log TV and movie views per day using Jellyfin API ✅ Completed
- Save to `<date>.media.json` or embed into frontmatter ✅ Completed
- Surface watched content optionally below entry or in archive ✅ Completed
- Support for optional filtering: “Show entries with movies/TV” ✅ Completed
- Add “Today I watched…” or “This story reminded me of…” prompts if media exists
- Reuse Jellyfin API setup already in use for music enrichment ✅ Completed

## Phase 6: Insight, Patterning, and Personalization (planned)
- Filter archive view by mood, energy, tags
  - Compact filter bar above the archive with emoji + text chips for mood/energy
  - Tag pills for custom keywords; multi-select toggles entries instantly
- Mood/energy calendar view (heatmap style)
  - Month grid colored by dominant mood or energy intensity
  - Hover or tap shows mood label and entry count; accessible color scale
- Personal time capsule: “Send to Future Me”
  - Author chooses future date and optional reminder email/notification
  - Entry resurfaces on that date as a prompt with the original text
- Prompt lane selector: Sensory | Reflective | Planning | Memory
  - Dropdown persists last choice in localStorage; default lane is Reflective
  - Lane influences which prompt set is served or which time-capsule message displays
- Micro-nudge fallback when text area is empty
  - After 5s of inactivity in an empty editor, show subtle “Need a seed?” link
  - Clicking inserts a gentle one-line starter or pulls a random prompt

## Design Guardrails
- Prioritize warmth and ultra-low friction above all else.
- Markdown format for longevity and openness.
- Clear separation of static UI and API backend (Jinja2 templates integrated).
