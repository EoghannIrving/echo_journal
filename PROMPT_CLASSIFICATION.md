# Prompt Creation and Classification

Echo Journal selects and organizes prompts by balancing the user's mood and energy with the cognitive demands of each question. Prompts are described by an **anchor** level and one or more strategy **tags**.

## 1. Anchor ↔ Mood/Energy Mapping

Anchor levels reflect the depth of emotional or cognitive engagement required. The app uses the user's `mood` and `energy` to select a prompt with an appropriate anchor.

| Anchor | Description |
| ------ | ----------- |
| `micro` | Ultra-light prompts. One word, emoji, or phrase. Ideal for 10-second journaling. |
| `soft` | Gentle observational or sensory prompts. Easy to start, low emotional load. |
| `moderate` | Encourages light reflection or meaning-making. Suitable for most states. |
| `strong` | Deep narrative, emotional, or introspective prompts. Requires focus or readiness. |

### Anchor Selection Logic

```python
# Determine allowed anchor levels based on mood and energy
def get_valid_anchors(mood: str, energy: int) -> list[str]:
    anchors = []

    if energy == 1:
        if mood in {"drained", "self-doubt", "sad"}:
            return ["micro"]
        else:
            return ["micro", "soft"]

    if energy == 2:
        if mood in {"sad", "meh", "self-doubt", "drained"}:
            anchors.append("soft")
        else:
            anchors.extend(["soft", "moderate"])

    if energy == 3:
        anchors.append("moderate")
        if mood in {"joyful", "focused", "energized"}:
            anchors.append("strong")

    if energy >= 4:
        anchors.extend(["moderate", "strong"])

    if mood in {"sad", "meh", "self-doubt"} and "soft" not in anchors:
        anchors.insert(0, "soft")

    if mood == "self-doubt" and "micro" not in anchors:
        anchors.insert(0, "micro")

    return anchors
```

This logic ensures:

- `micro` is always available for low energy, and exclusively for emotionally shut-down states.
- `soft` is broadly available but contextually filtered.
- `moderate` and `strong` are reserved for when energy and engagement are viable.

## 2. Core Prompt Strategies (Tags)

Each prompt is labeled with one or more strategy tags that describe its cognitive or emotional approach.

| Tag | Description |
| --- | ----------- |
| `senses` | Focus on describing sensory details (sight, sound, touch, etc.). |
| `context` | Ask for backstory, location, or events leading up to something. |
| `scene` | Describe a moment as if it were a scene in a painting or movie. |
| `contrast` | Explore differences, opposites, or changes. |
| `list` | List-based prompts, often with elaboration (e.g., "name 3 things and why"). |
| `mood` | Ask about emotional state and its causes or influences. |
| `hypothetical` | Use imagined scenarios to prompt reflection. |
| `deep` | Invite meaning-making or emotional depth (e.g., "why did it matter?"). |
| `temporal` | Time-anchored (e.g., "this morning," "looking back," "today"). |
| `narrative` | Encourage storytelling or sequential recounting of events. |

## 3. Assigning Strategy Tags

Use pattern matching or semantic cues to detect the dominant technique in a prompt. Most prompts should have one or two dominant tags.

### Heuristic Keyword Matching

Each tag has associated keywords or phrases. If a prompt contains one, assign the tag.

| Tag | Keywords (partial list) |
| --- | ----------------------- |
| `senses` | describe, texture, smell, heard, saw, noticed |
| `context` | where, what led, before, happened earlier |
| `scene` | scene, picture, frame, visual |
| `contrast` | opposite, both, and, contrast, flip side |
| `list` | list, three, several, name 5, top 3 |
| `mood` | feel, emotion, influenced, how you felt |
| `hypothetical` | if you could, imagine, what if, pretend |
| `deep` | why, significance, meaning, matter, value |
| `temporal` | morning, evening, today, now, this week, earlier |
| `narrative` | story, tell, happened, interaction, describe a moment |

## 4. Assigning an Anchor

Anchor assignment is based on emotional intensity, cognitive load, and prompt length.

| Anchor | Assign if prompt… |
| ------ | ------------------ |
| `micro` | Can be answered in one word or emoji. e.g., "Mood in 3 words." |
| `soft` | Asks for a list or sensory observation. Low-pressure entry. |
| `moderate` | Asks for some reflection, context, or simple narrative. |
| `strong` | Requires emotional depth, personal meaning, or storytelling. |

### Examples

- **Micro**: "Pick an emoji for your day." → `micro`
- **Soft**: "What’s something you saw today?" → `soft`, `senses`
- **Moderate**: "What’s something that surprised you and why?" → `moderate`, `contrast`, `deep`
- **Strong**: "Tell the story of a time you felt invisible." → `strong`, `narrative`, `mood`

With this system, Echo Journal prompts remain context-sensitive, emotionally aware, and easy to grow with.

