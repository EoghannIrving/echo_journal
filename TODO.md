# TODO

This list captures planned work from the project roadmap. Completed items from earlier phases are omitted.

- [ ] **Expanded Archive view**
  - [X] Display metadata markers (location, weather, photo indicator)
  - [ ] Optional sorting and filtering by available enrichment
  - [X] Rework Archive page layout to be more compact.

- [X] **Stats dashboard**
  - [X] Show entry counts by week, month and year
  - [X] Provide word count statistics
  - [X] Optional "streak" tracking for consecutive days or weeks

- [ ] **Metadata parsing improvements**
  - [X] Unify parsing logic and support frontmatter if needed
  - [ ] Document YAML frontmatter structure with `location`, `weather` and `photos` as well as other keys
  - [X] Parse this frontmatter in `archive_view` to expose icon flags
  - [ ] Use `pyyaml` to read the frontmatter delimited by `---` at the top of each entry
  - [X] Maintain compatibility with legacy `.md` entries

- [ ] **Enrichment integration prep**
  - [ ] Support Immich photo integration
  - [X] Add geolocation capture
  - [X] Query a weather API for recent conditions
  - [ ] Pull a "Word of the Day" and add that to the journal
  - [ ] Pull a "Fact of the Day" and add that to the journal
  - [ ] Record save time in front matter
  - [ ] AI assisted prompts / "Need inspiration?" feature
  - [ ] Optional "New Prompt" link with hover/tap hint
  - [ ] Evaluate secure remote access options (auth or VPN/proxy)
  - [ ] Settings to allow for turning off optional integrations

