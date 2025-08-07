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
