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
  - AI-assisted prompts (“Need inspiration?” feature).
  - Optional "New Prompt" link to gently refresh the daily suggestion if it doesn't resonate.
    - Subtle secondary text that fades in on hover/tap.
    - Client-side localStorage ensures the prompt stays consistent after saving.
  - Optional secure remote access (auth, VPN/reverse proxy).

## Design Guardrails
- Prioritize warmth and ultra-low friction above all else.
- Markdown format for longevity and openness.
- Clear separation of static UI and API backend (Jinja2 templates integrated).
