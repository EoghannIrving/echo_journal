# YAML Frontmatter Reference

Each journal entry begins with a YAML block. These fields are parsed whenever an entry is saved or displayed.

## Example

```yaml
location: Example Place
weather: 18°C code 1
save_time: Evening
wotd: luminous
wotd_def: emitting light
category: Gratitude
mood: joyful
energy: energized
fact: 42 is the answer
```

## Field details

| Field | Purpose | Application usage |
| ----- | ------- | ----------------- |
| `location` | Human readable label from browser geolocation. | Shown with a 📍 icon in archive and entry views. |
| `weather` | Temperature and weather code from Open‑Meteo. | Parsed by `format_weather` to show an icon; codes are mapped to words for mouseover titles. |
| `save_time` | Morning/Afternoon/Evening/Night recorded at save time. | Provides context for when the entry was written. Uses the client `tz_offset` when supplied. |
| `wotd` | Wordnik word of the day. | Displayed in the entry sidebar and as an icon in the archive list. |
| `wotd_def` | Definition for the word of the day. | Shown alongside the word in entry views. |
| `category` | Prompt category selected when saving. | Stored for filtering and prompt history. |
| `mood` | Mood chosen when saving. | Displayed in entry views and sortable in the archive. |
| `energy` | Energy level chosen when saving. | Used to tailor prompts and shown in metadata. |
| `fact` | Numbers API fact of the day. | Displayed in the entry sidebar. |

Additional keys may be introduced in future integrations. Unknown keys are ignored.

## Energy level mapping

Energy selections from the UI are translated to integers before hitting `/api/new_prompt`.
This allows the backend to score prompts based on numeric intensity.

| Energy | Value |
| ------ | ----- |
| `drained` | 1 |
| `low` | 2 |
| `ok` | 3 |
| `energized` | 4 |

## Media metadata JSON files

Photos, music, and video history are stored separately from the YAML frontmatter.
When integrations are enabled, the application creates JSON files under the
`.meta/` directory next to your journal files:

- `<date>.photos.json` for Immich photo links
- `<date>.songs.json` for music listening history
- `<date>.media.json` for Jellyfin movies and TV

These files are loaded when viewing or filtering entries so the interface can
show thumbnails, track counts, and other details without bloating the
frontmatter itself.
