"""Endpoint tests for the Echo Journal application."""

# Disable fixture name shadowing warnings in test functions.
# pytest expects tests to accept the ``test_client`` fixture as an argument,
# which triggers ``redefined-outer-name`` from pylint.
#
# pylint: disable=redefined-outer-name,too-many-lines,import-outside-toplevel,multiple-imports,wrong-import-order,unused-argument

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, date, timedelta
from pathlib import Path
import base64
import logging
import httpx  # pylint: disable=import-error

import aiofiles  # type: ignore  # pylint: disable=import-error
import pytest  # pylint: disable=import-error
import ai_prompt_utils
from fastapi.testclient import TestClient  # pylint: disable=import-error

# Prepare required directories before importing the app
ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path(tempfile.gettempdir()) / "ej_app"
STATIC_DIR = APP_DIR / "static"
PROMPTS_FILE = APP_DIR / "prompts.yaml"
DATA_ROOT = Path(tempfile.gettempdir()) / "ej_journals"

TEMPLATES_DIR = ROOT / "templates"

os.environ["APP_DIR"] = str(APP_DIR)
os.environ["DATA_DIR"] = str(DATA_ROOT)
os.environ["STATIC_DIR"] = str(STATIC_DIR)
os.environ["PROMPTS_FILE"] = str(PROMPTS_FILE)
os.environ["TEMPLATES_DIR"] = str(TEMPLATES_DIR)

# Ensure directories for the application exist before importing ``main``
STATIC_DIR.mkdir(parents=True, exist_ok=True)
DATA_ROOT.mkdir(parents=True, exist_ok=True)
# copy prompts file if not already
if not PROMPTS_FILE.exists():
    shutil.copy(ROOT / "prompts.yaml", PROMPTS_FILE)

# Make sure the repository root is on ``sys.path`` so ``main`` can be imported
sys.path.insert(0, str(ROOT))

# Import the application after environment setup
import main  # type: ignore  # pylint: disable=wrong-import-position
import weather_utils  # pylint: disable=wrong-import-position
import immich_utils  # pylint: disable=wrong-import-position
import jellyfin_utils  # pylint: disable=wrong-import-position


@pytest.fixture()
def test_client(tmp_path, monkeypatch):
    """Return a TestClient instance using a temporary journals directory."""
    journals = tmp_path / "journals"
    journals.mkdir()
    monkeypatch.setattr(main, "DATA_DIR", journals)
    return TestClient(main.app)


def test_index_returns_page(test_client):
    """Requesting the index should return the journal page."""
    resp = test_client.get("/")
    assert resp.status_code == 200
    assert "Echo Journal" in resp.text


def test_restart_notice_shown_when_yesterday_missing(test_client):
    """Index shows restart message when there's no entry for yesterday."""
    two_days_ago = (date.today() - timedelta(days=2)).isoformat()
    (main.DATA_DIR / f"{two_days_ago}.md").write_text("entry", encoding="utf-8")
    resp = test_client.get("/")
    assert "Restart from today?" in resp.text


def test_restart_notice_absent_when_yesterday_exists(test_client):
    """Restart message not shown if yesterday's entry exists."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    (main.DATA_DIR / f"{yesterday}.md").write_text("entry", encoding="utf-8")
    resp = test_client.get("/")
    assert "Restart from today?" not in resp.text


def test_save_entry_and_retrieve(test_client):
    """Entries can be saved and later retrieved."""
    payload = {"date": "2020-01-01", "content": "entry", "prompt": "prompt"}
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    file_path = main.DATA_DIR / "2020-01-01.md"
    assert file_path.exists()
    resp2 = test_client.get("/entry/2020-01-01")
    assert resp2.status_code == 200
    assert "prompt" in resp2.json()["content"]


def test_save_entry_records_time(test_client, monkeypatch):
    """Saving an entry records the time of day in frontmatter."""
    monkeypatch.setattr(weather_utils, "time_of_day_label", lambda: "Evening")
    monkeypatch.setattr(main, "time_of_day_label", lambda: "Evening")
    payload = {"date": "2020-01-03", "content": "entry", "prompt": "prompt"}
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    file_path = main.DATA_DIR / "2020-01-03.md"
    text = file_path.read_text(encoding="utf-8")
    assert "save_time: Evening" in text


def test_word_of_day_in_frontmatter(test_client, monkeypatch):
    """Wordnik word of the day is saved in frontmatter when available."""

    async def fake_word():
        return "serendipity", "fortunate discovery"

    monkeypatch.setattr(weather_utils, "fetch_word_of_day", fake_word)
    payload = {"date": "2020-10-10", "content": "entry", "prompt": "prompt"}
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    text = (main.DATA_DIR / "2020-10-10.md").read_text(encoding="utf-8")
    assert "wotd: serendipity" in text
    assert "wotd_def: fortunate discovery" in text


def test_wordnik_disabled_in_frontmatter(test_client, monkeypatch):
    """Wordnik data should be omitted when integration is disabled."""

    async def fake_word():
        return "serendipity", "fortunate discovery"

    monkeypatch.setattr(weather_utils, "fetch_word_of_day", fake_word)
    payload = {
        "date": "2020-10-11",
        "content": "entry",
        "prompt": "prompt",
        "integrations": {"wordnik": False},
    }
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    text = (main.DATA_DIR / "2020-10-11.md").read_text(encoding="utf-8")
    assert "wotd:" not in text
    assert "wotd_def:" not in text


def test_category_saved_in_frontmatter(test_client):
    """Prompt category should be stored in frontmatter when provided."""
    payload = {
        "date": "2020-12-12",
        "content": "entry",
        "prompt": "prompt",
        "category": "Fun",
    }
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    text = (main.DATA_DIR / "2020-12-12.md").read_text(encoding="utf-8")
    assert "category: Fun" in text


def test_weather_saved_when_provided(test_client):
    """Weather data is stored in frontmatter when supplied."""
    payload = {
        "date": "2021-01-01",
        "content": "entry",
        "prompt": "prompt",
        "location": {"lat": 1, "lon": 2, "accuracy": 0, "label": "X"},
        "weather": {"temperature": 20, "code": 1},
    }
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    text = (main.DATA_DIR / "2021-01-01.md").read_text(encoding="utf-8")
    assert "weather: 20°C code 1" in text


def test_mood_and_energy_saved(test_client):
    """Selected mood and energy values are stored in frontmatter."""
    payload = {
        "date": "2021-04-01",
        "content": "entry",
        "prompt": "prompt",
        "mood": "joyful",
        "energy": "energized",
    }
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    text = (main.DATA_DIR / "2021-04-01.md").read_text(encoding="utf-8")
    assert "mood: joyful" in text
    assert "energy: energized" in text


def test_save_entry_missing_fields(test_client):
    """Saving with missing required fields should return an error."""
    resp = test_client.post("/entry", json={"date": "2020-01-02"})
    assert resp.status_code == 400
    assert resp.json()["status"] == "error"


def test_get_entry_not_found(test_client):
    """Fetching a non-existent entry should return 404."""
    resp = test_client.get("/entry/1999-01-01")
    assert resp.status_code == 404


def test_load_entry(test_client):
    """load_entry endpoint should return the entry text without headers."""
    (main.DATA_DIR / "2020-02-02.md").write_text(
        "# Prompt\nA\n\n# Entry\nB", encoding="utf-8"
    )
    resp = test_client.get("/entry", params={"entry_date": "2020-02-02"})
    assert resp.status_code == 200
    assert resp.json()["content"] == "B"


def test_load_entry_windows_newlines(test_client):
    """load_entry handles Windows CRLF line endings."""
    (main.DATA_DIR / "2020-02-03.md").write_text(
        "# Prompt\r\nA\r\n\r\n# Entry\r\nB", encoding="utf-8"
    )
    resp = test_client.get("/entry", params={"entry_date": "2020-02-03"})
    assert resp.status_code == 200
    assert resp.json()["content"] == "B"


def test_load_entry_case_insensitive_headers(test_client):
    """load_entry accepts lowercase section headers."""
    (main.DATA_DIR / "2020-02-04.md").write_text(
        "# prompt\nA\n\n# entry\nB", encoding="utf-8"
    )
    resp = test_client.get("/entry", params={"entry_date": "2020-02-04"})
    assert resp.status_code == 200
    assert resp.json()["content"] == "B"


def test_load_entry_missing(test_client):
    """Loading a missing entry should return 404."""
    resp = test_client.get("/entry", params={"entry_date": "2000-01-01"})
    assert resp.status_code == 404


def test_view_entry_existing(test_client):
    """Existing entries can be viewed in read-only mode."""
    (main.DATA_DIR / "2020-03-03.md").write_text(
        "# Prompt\nA\n\n# Entry\nB", encoding="utf-8"
    )
    resp = test_client.get("/archive/2020-03-03")
    assert resp.status_code == 200
    assert "B" in resp.text
    assert "journal-html" in resp.text


def test_view_entry_sanitized(test_client):
    """Malicious HTML in entries should be escaped."""
    content = "# Prompt\nA\n\n# Entry\n<script>alert('X')</script>"
    (main.DATA_DIR / "2020-03-05.md").write_text(content, encoding="utf-8")
    resp = test_client.get("/archive/2020-03-05")
    assert resp.status_code == 200
    assert "<script>alert('X')" not in resp.text
    assert "&lt;script&gt;" in resp.text


def test_view_entry_multiline_prompt(test_client):
    """Prompts spanning multiple lines should render correctly."""
    content = "# Prompt\nLine1\nLine2\n\n# Entry\nBody"
    (main.DATA_DIR / "2020-03-04.md").write_text(content, encoding="utf-8")
    resp = test_client.get("/archive/2020-03-04")
    assert resp.status_code == 200
    assert "Line1" in resp.text and "Line2" in resp.text
    assert "Body" in resp.text


def test_view_entry_malformed(test_client):
    """Malformed filenames should return 404."""
    (main.DATA_DIR / "bad.md").write_text("No headings here", encoding="utf-8")
    resp = test_client.get("/archive/bad")
    assert resp.status_code == 404


def test_view_entry_missing(test_client):
    """Requesting a missing entry by date returns 404."""
    resp = test_client.get("/archive/2020-04-04")
    assert resp.status_code == 404


def test_archive_view(test_client):
    """The archive page lists all valid entries."""
    (main.DATA_DIR / "2020-05-01.md").write_text(
        "# Prompt\nP\n\n# Entry\nE1", encoding="utf-8"
    )
    (main.DATA_DIR / "2020-05-02.md").write_text(
        "# Prompt\nP\n\n# Entry\nE2", encoding="utf-8"
    )
    (main.DATA_DIR / "badfile.md").write_text("oops", encoding="utf-8")
    subdir = main.DATA_DIR / "2021"
    subdir.mkdir()
    (subdir / "2021-06-01.md").write_text(
        "# Prompt\nP\n\n# Entry\nE3", encoding="utf-8"
    )
    resp = test_client.get("/archive")
    assert resp.status_code == 200
    assert "2020-05-01" in resp.text
    assert "2020-05-02" in resp.text
    assert "2021-06-01" in resp.text
    assert "badfile" in resp.text


def test_archive_view_unreadable_file(test_client, monkeypatch):
    """Unreadable files should be skipped without error."""
    bad_path = main.DATA_DIR / "2020-07-07.md"
    bad_path.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")

    orig_open = aiofiles.open

    def open_mock(file, *args, **kwargs):
        if Path(file) == bad_path:
            raise OSError("cannot read")
        return orig_open(file, *args, **kwargs)

    monkeypatch.setattr(aiofiles, "open", open_mock)

    resp = test_client.get("/archive")
    assert resp.status_code == 200
    assert "2020-07-07" not in resp.text


def test_view_entry_unreadable_file(test_client, monkeypatch):
    """Unreadable entry files should return a 500 error."""
    bad_path = main.DATA_DIR / "2020-08-08.md"
    bad_path.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")

    orig_open = aiofiles.open

    def open_mock(file, *args, **kwargs):
        if Path(file) == bad_path:
            raise OSError("cannot read")
        return orig_open(file, *args, **kwargs)

    monkeypatch.setattr(aiofiles, "open", open_mock)

    resp = test_client.get("/archive/2020-08-08")
    assert resp.status_code == 500


def test_view_entry_uses_frontmatter(test_client):
    """Location and weather come from frontmatter when viewing entries."""
    content = (
        "---\n"
        "location: Testville\n"
        "weather: 12\u00b0C code 1\n"
        "photos: []\n"
        "---\n"
        "# Prompt\nP\n\n# Entry\nE"
    )
    (main.DATA_DIR / "2020-09-09.md").write_text(content, encoding="utf-8")
    resp = test_client.get("/archive/2020-09-09")
    assert resp.status_code == 200
    assert "Testville" in resp.text
    assert "12\u00b0C" in resp.text


def test_view_entry_no_metadata_hidden(test_client):
    """Location and weather divs are hidden without metadata."""
    (main.DATA_DIR / "2020-09-10.md").write_text(
        "# Prompt\nP\n\n# Entry\nE", encoding="utf-8"
    )
    resp = test_client.get("/archive/2020-09-10")
    assert resp.status_code == 200
    assert 'id="location-display"' in resp.text
    assert "hidden" in resp.text.split('id="location-display"')[1].split(">")[0]
    assert 'id="weather-display"' in resp.text
    assert "hidden" in resp.text.split('id="weather-display"')[1].split(">")[0]


def test_save_entry_invalid_date(test_client):
    """Entries with malformed date strings should return an error."""
    payload = {"date": "2020-13-40", "content": "bad", "prompt": "p"}
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 400
    assert resp.json()["status"] == "error"
    assert not (main.DATA_DIR / "2020-13-40.md").exists()


def test_save_entry_path_traversal(test_client):
    """Directory traversal attempts should be rejected with an error."""
    malicious = "../malicious"
    payload = {"date": malicious, "content": "x", "prompt": "y"}
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 400
    assert resp.json()["status"] == "error"
    expected = main.DATA_DIR / "malicious.md"
    assert not expected.exists()


def test_get_entry_invalid_date(test_client):
    """Invalid date segments should yield a 404 response."""
    resp = test_client.get("/entry/invalid-date")
    assert resp.status_code == 404


def test_view_entry_traversal(test_client):
    """Path traversal attempts in view routes should be denied."""
    resp = test_client.get("/archive/../../etc/passwd")
    assert resp.status_code == 404


def test_load_entry_empty_date(test_client):
    """Empty entry_date should return a 404 error."""
    resp = test_client.get("/entry", params={"entry_date": ""})
    assert resp.status_code == 404


def test_stats_page_counts(test_client):
    """Stats page aggregates entry and word counts."""
    (main.DATA_DIR / "2022-01-01.md").write_text(
        "# Prompt\nP\n\n# Entry\none two",
        encoding="utf-8",
    )
    (main.DATA_DIR / "2022-01-02.md").write_text(
        "# Prompt\nP\n\n# Entry\nthree",
        encoding="utf-8",
    )
    (main.DATA_DIR / "2022-02-01.md").write_text(
        "# Prompt\nP\n\n# Entry\nfour five six",
        encoding="utf-8",
    )

    resp = test_client.get("/stats")
    assert resp.status_code == 200
    assert "Total entries: 3" in resp.text
    assert "Total words: 6" in resp.text


def test_stats_page_streaks(test_client):
    """Stats page reports correct day and week streaks."""
    dates = [
        "2022-01-03",
        "2022-01-04",
        "2022-01-05",
        "2022-01-10",
        "2022-01-17",
        "2022-01-31",
    ]
    for d in dates:
        (main.DATA_DIR / f"{d}.md").write_text(
            "# Prompt\nP\n\n# Entry\nE",
            encoding="utf-8",
        )

    resp = test_client.get("/stats")
    assert resp.status_code == 200
    assert "Current daily streak: 1" in resp.text
    assert "Longest daily streak: 3" in resp.text
    assert "Current weekly streak: 1" in resp.text
    assert "Longest weekly streak: 3" in resp.text


def test_archive_filter_and_sort(test_client):
    """Archive endpoint supports filtering and sorting by metadata."""
    entry1 = (
        "---\n"
        "location: Btown\n"
        "weather: 10\u00b0C code 1\n"
        "photos: []\n"
        "---\n"
        "# Prompt\nP1\n\n# Entry\nE1"
    )
    entry2 = (
        "---\n"
        "weather: 12\u00b0C code 2\n"
        "photos: []\n"
        "---\n"
        "# Prompt\nP2\n\n# Entry\nE2"
    )
    entry3 = """---
location: Atown
photos: []
---
# Prompt
P3

# Entry
E3"""
    (main.DATA_DIR / "2021-07-01.md").write_text(entry1, encoding="utf-8")
    (main.DATA_DIR / "2021-07-02.md").write_text(entry2, encoding="utf-8")
    (main.DATA_DIR / "2021-07-03.md").write_text(entry3, encoding="utf-8")

    resp = test_client.get("/archive", params={"filter": "has_location"})
    assert resp.status_code == 200
    assert "2021-07-01" in resp.text
    assert "2021-07-03" in resp.text
    assert "2021-07-02" not in resp.text

    resp2 = test_client.get("/archive", params={"sort_by": "location"})
    assert resp2.status_code == 200
    # When sorted by location, Atown (2021-07-03) should come before Btown
    assert resp2.text.find("2021-07-03") < resp2.text.find("2021-07-01")


def test_archive_filter_has_photos(test_client):
    """Entries can be filtered by those containing photos."""
    md1 = main.DATA_DIR / "2024-01-01.md"
    md1.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")
    photos_path = main.DATA_DIR / "2024-01-01.photos.json"
    photos_path.write_text(json.dumps([{"url": "u", "thumb": "t"}]), encoding="utf-8")

    md2 = main.DATA_DIR / "2024-01-02.md"
    md2.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")

    resp = test_client.get("/archive", params={"filter": "has_photos"})
    assert resp.status_code == 200
    assert "2024-01-01" in resp.text
    assert "2024-01-02" not in resp.text


def test_archive_current_month_open(test_client):
    """The current month's details section should be expanded."""
    today = datetime.now().date()
    current = today.strftime("%Y-%m-%d")
    (main.DATA_DIR / f"{current}.md").write_text(
        "# Prompt\nP\n\n# Entry\nE", encoding="utf-8"
    )
    (main.DATA_DIR / "2000-01-01.md").write_text(
        "# Prompt\nP\n\n# Entry\nE", encoding="utf-8"
    )

    resp = test_client.get("/archive")
    assert resp.status_code == 200

    month = today.strftime("%Y-%m")
    summary = f'<summary class="cursor-pointer text-base font-medium">{month}</summary>'
    idx = resp.text.find(summary)
    assert idx != -1
    snippet = resp.text[max(0, idx - 50) : idx]
    assert "open" in snippet

    other_summary = (
        '<summary class="cursor-pointer text-base font-medium">2000-01</summary>'
    )
    idx2 = resp.text.find(other_summary)
    assert idx2 != -1
    snippet2 = resp.text[max(0, idx2 - 50) : idx2]
    assert "open" not in snippet2


def test_view_entry_shows_wotd(test_client):
    """Word of the day from frontmatter should appear in view page."""
    content = """---
wotd: luminous
wotd_def: emitting light
photos: []
---
# Prompt
P

# Entry
E"""
    (main.DATA_DIR / "2021-08-01.md").write_text(content, encoding="utf-8")
    resp = test_client.get("/archive/2021-08-01")
    assert resp.status_code == 200
    assert "luminous" in resp.text
    assert "emitting light" in resp.text


def test_archive_shows_wotd_icon(test_client):
    """Entries with a word of the day show an icon in the archive."""
    content = """---
wotd: zephyr
wotd_def: gentle breeze
photos: []
---
# Prompt
P

# Entry
E"""
    (main.DATA_DIR / "2021-09-09.md").write_text(content, encoding="utf-8")
    resp = test_client.get("/archive")
    assert resp.status_code == 200
    assert "📖" in resp.text


def test_save_entry_adds_photo_metadata(test_client, monkeypatch):
    """Saving an entry stores photo metadata from Immich."""

    async def fake_fetch(_date_str: str, media_type: str = "IMAGE"):
        _ = media_type
        return [
            {
                "id": "123",
                "originalFileName": "img1.jpg",
                "fileCreatedAt": "2023-01-01T12:00:00Z",
            }
        ]

    monkeypatch.setattr(immich_utils, "fetch_assets_for_date", fake_fetch)
    payload = {"date": "2023-01-01", "content": "entry", "prompt": "prompt"}
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    json_path = main.DATA_DIR / "2023-01-01.photos.json"
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data[0]["caption"] == "img1.jpg"
    assert data[0]["url"] == "/api/asset/123"
    assert data[0]["thumb"] == "/api/thumbnail/123?size=thumbnail"


def test_immich_disabled_skips_photo_metadata(test_client, monkeypatch):
    """Disabling Immich should prevent photo metadata from being saved."""

    async def fake_fetch(_date_str: str, media_type: str = "IMAGE"):
        _ = media_type
        return [
            {
                "id": "123",
                "originalFileName": "img1.jpg",
                "fileCreatedAt": "2023-01-01T12:00:00Z",
            }
        ]

    monkeypatch.setattr(immich_utils, "fetch_assets_for_date", fake_fetch)
    payload = {
        "date": "2023-01-02",
        "content": "entry",
        "prompt": "prompt",
        "integrations": {"immich": False},
    }
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    json_path = main.DATA_DIR / "2023-01-02.photos.json"
    assert not json_path.exists()


def test_save_entry_adds_song_metadata(test_client, monkeypatch):
    """Saving an entry stores song metadata from Jellyfin."""

    async def fake_fetch(_date_str: str):
        return [
            {"track": "t1", "artist": "a1", "plays": 3},
            {"track": "t2", "artist": "a2", "plays": 2},
        ]

    monkeypatch.setattr(jellyfin_utils, "fetch_top_songs", fake_fetch)
    payload = {"date": "2023-05-05", "content": "entry", "prompt": "prompt"}
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    json_path = main.DATA_DIR / "2023-05-05.songs.json"
    assert json_path.exists()
    songs = json.loads(json_path.read_text(encoding="utf-8"))
    assert songs[0]["track"] == "t1"
    assert songs[0]["artist"] == "a1"
    assert songs[0]["plays"] == 3


def test_save_entry_adds_media_metadata(test_client, monkeypatch):
    """Saving an entry stores movie/TV metadata from Jellyfin."""

    async def fake_fetch(_date_str: str):
        return [{"title": "Movie", "series": ""}]

    monkeypatch.setattr(jellyfin_utils, "fetch_daily_media", fake_fetch)
    payload = {"date": "2023-05-06", "content": "entry", "prompt": "prompt"}
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    json_path = main.DATA_DIR / "2023-05-06.media.json"
    assert json_path.exists()
    media = json.loads(json_path.read_text(encoding="utf-8"))
    assert media[0]["title"] == "Movie"


def test_jellyfin_disabled_skips_metadata(test_client, monkeypatch):
    """Disabling Jellyfin should skip song and media metadata saves."""

    async def fake_fetch_songs(_date_str: str):
        return [{"track": "t1", "artist": "a1", "plays": 1}]

    async def fake_fetch_media(_date_str: str):
        return [{"title": "Movie", "series": ""}]

    monkeypatch.setattr(jellyfin_utils, "fetch_top_songs", fake_fetch_songs)
    monkeypatch.setattr(jellyfin_utils, "fetch_daily_media", fake_fetch_media)
    payload = {
        "date": "2023-05-07",
        "content": "entry",
        "prompt": "prompt",
        "integrations": {"jellyfin": False},
    }
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    songs_path = main.DATA_DIR / "2023-05-07.songs.json"
    media_path = main.DATA_DIR / "2023-05-07.media.json"
    assert not songs_path.exists()
    assert not media_path.exists()


def test_backfill_song_metadata(test_client, monkeypatch):
    """Backfill endpoint creates songs.json for existing entries."""

    md_path = main.DATA_DIR / "2023-06-06.md"
    md_path.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")

    async def fake_fetch(date_str: str):
        assert date_str == "2023-06-06"
        return [{"track": "t", "artist": "a", "plays": 1}]

    monkeypatch.setattr(jellyfin_utils, "fetch_top_songs", fake_fetch)

    resp = test_client.post("/api/backfill_songs")

    assert resp.status_code == 200
    assert resp.json()["added"] == 1
    songs_path = main.DATA_DIR / "2023-06-06.songs.json"
    assert songs_path.exists()


def test_archive_shows_photo_icon(test_client, monkeypatch):
    """Entries with a companion photo file show an icon in the archive."""

    async def fake_fetch(_date_str: str, media_type: str = "IMAGE"):
        _ = media_type
        return [
            {
                "id": "123",
                "originalFileName": "img1.jpg",
                "fileCreatedAt": "2023-02-02T08:00:00Z",
            }
        ]

    monkeypatch.setattr(immich_utils, "fetch_assets_for_date", fake_fetch)
    payload = {"date": "2023-02-02", "content": "e", "prompt": "p"}
    test_client.post("/entry", json=payload)

    resp = test_client.get("/archive")
    assert resp.status_code == 200
    assert "📸" in resp.text


def test_view_entry_updates_photo_metadata(test_client, monkeypatch):
    """Viewing an entry should poll Immich for new photos."""
    called = {"flag": False}

    async def fake_update(_date, _path):
        called["flag"] = True

    monkeypatch.setattr(main, "update_photo_metadata", fake_update)

    (main.DATA_DIR / "2023-03-03.md").write_text(
        "# Prompt\nP\n\n# Entry\nE", encoding="utf-8"
    )

    resp = test_client.get("/archive/2023-03-03")
    assert resp.status_code == 200
    assert called["flag"]


def test_view_entry_shows_photos(test_client):
    """Thumbnail images from photos.json are displayed on the entry page."""
    md_path = main.DATA_DIR / "2023-04-04.md"
    md_path.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")
    photos = [
        {
            "url": "http://example.com/full1",
            "thumb": "http://example.com/t1",
            "caption": "one",
        },
        {
            "url": "http://example.com/full2",
            "thumb": "http://example.com/t2",
            "caption": "two",
        },
    ]
    json_path = main.DATA_DIR / "2023-04-04.photos.json"
    json_path.write_text(json.dumps(photos), encoding="utf-8")

    resp = test_client.get("/archive/2023-04-04")
    assert resp.status_code == 200
    assert "http://example.com/t1" in resp.text
    assert "http://example.com/t2" in resp.text


def test_view_entry_shows_songs(test_client):
    """Song info from songs.json should appear on the entry page."""

    md_path = main.DATA_DIR / "2023-07-07.md"
    md_path.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")
    songs = [
        {"track": "s1", "artist": "a1", "plays": 2},
        {"track": "s2", "artist": "a2", "plays": 1},
    ]
    json_path = main.DATA_DIR / "2023-07-07.songs.json"
    json_path.write_text(json.dumps(songs), encoding="utf-8")

    resp = test_client.get("/archive/2023-07-07")
    assert resp.status_code == 200
    assert "s1" in resp.text
    assert "a1" in resp.text


def test_archive_shows_song_icon(test_client):
    """Entries with songs show an icon in the archive."""

    md_path = main.DATA_DIR / "2024-02-02.md"
    md_path.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")
    json_path = main.DATA_DIR / "2024-02-02.songs.json"
    json_path.write_text(json.dumps([{"track": "t", "artist": "a"}]), encoding="utf-8")

    resp = test_client.get("/archive")
    assert resp.status_code == 200
    assert "🎵" in resp.text


def test_archive_filter_has_songs(test_client):
    """Entries can be filtered by those containing songs."""

    md1 = main.DATA_DIR / "2025-01-01.md"
    md1.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")
    songs_path = main.DATA_DIR / "2025-01-01.songs.json"
    songs_path.write_text(json.dumps([{"track": "t", "artist": "a"}]), encoding="utf-8")

    md2 = main.DATA_DIR / "2025-01-02.md"
    md2.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")

    resp = test_client.get("/archive", params={"filter": "has_songs"})
    assert resp.status_code == 200
    assert "2025-01-01" in resp.text
    assert "2025-01-02" not in resp.text


def test_archive_sort_by_songs(test_client):
    """Entries can be sorted by songs metadata."""

    md1 = main.DATA_DIR / "2026-01-01.md"
    md1.write_text("# Prompt\nP1\n\n# Entry\nE1", encoding="utf-8")
    path1 = main.DATA_DIR / "2026-01-01.songs.json"
    path1.write_text(json.dumps([{"track": "b"}]), encoding="utf-8")

    md2 = main.DATA_DIR / "2026-01-02.md"
    md2.write_text("# Prompt\nP2\n\n# Entry\nE2", encoding="utf-8")
    path2 = main.DATA_DIR / "2026-01-02.songs.json"
    path2.write_text(json.dumps([{"track": "a"}]), encoding="utf-8")

    resp = test_client.get("/archive", params={"sort_by": "songs"})
    assert resp.status_code == 200
    assert resp.text.find("2026-01-02") < resp.text.find("2026-01-01")


def test_view_entry_shows_media(test_client):
    """Media info from media.json should appear on the entry page."""

    md_path = main.DATA_DIR / "2027-01-01.md"
    md_path.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")
    media_items = [
        {"title": "Ep1", "series": "Show"},
        {"title": "Movie", "series": ""},
    ]
    json_path = main.DATA_DIR / "2027-01-01.media.json"
    json_path.write_text(json.dumps(media_items), encoding="utf-8")

    resp = test_client.get("/archive/2027-01-01")
    assert resp.status_code == 200
    assert "Show - Ep1" in resp.text
    assert "Movie" in resp.text


def test_archive_filter_has_media(test_client):
    """Entries can be filtered by those containing movies/TV."""

    md1 = main.DATA_DIR / "2028-01-01.md"
    md1.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")
    media_path = main.DATA_DIR / "2028-01-01.media.json"
    media_path.write_text(json.dumps([{"title": "M"}]), encoding="utf-8")

    md2 = main.DATA_DIR / "2028-01-02.md"
    md2.write_text("# Prompt\nP\n\n# Entry\nE", encoding="utf-8")

    resp = test_client.get("/archive", params={"filter": "has_media"})
    assert resp.status_code == 200
    assert "2028-01-01" in resp.text
    assert "2028-01-02" not in resp.text


def test_asset_proxy_download(test_client, monkeypatch):
    """Asset proxy endpoint should fetch original file from Immich."""

    class FakeClient:
        """Async HTTP client stub used to capture requests."""

        def __init__(self):
            self.request_url = None
            self.request_headers = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None):
            """Record request details and return a fake image response."""
            self.request_url = url
            self.request_headers = headers

            class Resp:  # pylint: disable=too-few-public-methods
                """Minimal response stub returned by ``FakeClient``."""

                status_code = 200
                headers = {"content-type": "image/jpeg"}
                content = b"img"

            return Resp()

    client = FakeClient()
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(main, "IMMICH_URL", "http://example/api")
    monkeypatch.setattr(main, "IMMICH_API_KEY", "secret")

    resp = test_client.get("/api/asset/abc")

    assert resp.status_code == 200
    assert resp.content == b"img"
    assert resp.headers["content-type"] == "image/jpeg"
    assert client.request_url == "http://example/api/assets/abc/original"
    assert client.request_headers == {"x-api-key": "secret"}


def test_reverse_geocode_network_error(test_client, monkeypatch):
    """Network failures should return a 502 error instead of crashing."""

    class BadClient:
        """Minimal async client that always raises a connection error."""

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(
            self, url, params=None, headers=None, timeout=None
        ):  # pylint: disable=unused-argument
            """Simulate a failed request."""
            raise httpx.ConnectError("boom", request=httpx.Request("GET", url))

    monkeypatch.setattr(main.httpx, "AsyncClient", BadClient)

    resp = test_client.get("/api/reverse_geocode", params={"lat": 1.0, "lon": 2.0})

    assert resp.status_code == 502
    assert resp.json()["detail"] == "Reverse geocoding failed"


def test_new_prompt_endpoint(test_client, monkeypatch):
    """/api/new_prompt returns a generated prompt."""

    captured: dict[str, object] = {}

    async def fake_prompt(*, mood=None, energy=None, debug=False):
        captured["mood"] = mood
        captured["energy"] = energy
        captured["debug"] = debug
        return {"prompt": "P", "category": "Test"}

    monkeypatch.setattr(main, "generate_prompt", fake_prompt)

    resp = test_client.get("/api/new_prompt?mood=ok&energy=2")

    assert resp.status_code == 200
    assert resp.json() == {"prompt": "P", "category": "Test"}
    assert captured["mood"] == "ok"
    assert captured["energy"] == 2
    assert captured["debug"] is False


def test_new_prompt_endpoint_no_params(test_client, monkeypatch):
    """/api/new_prompt still returns a prompt without optional params."""

    async def fake_prompt(*, mood=None, energy=None, debug=False):
        assert mood is None and energy is None and debug is False
        return {"prompt": "P", "category": "Test"}

    monkeypatch.setattr(main, "generate_prompt", fake_prompt)

    resp = test_client.get("/api/new_prompt")

    assert resp.status_code == 200
    assert resp.json() == {"prompt": "P", "category": "Test"}


def test_new_prompt_endpoint_debug_param(test_client, monkeypatch):
    """/api/new_prompt forwards the debug flag."""

    captured: dict[str, object] = {}

    async def fake_prompt(*, mood=None, energy=None, debug=False):
        captured["debug"] = debug
        return {"prompt": "P", "category": "Test"}

    monkeypatch.setattr(main, "generate_prompt", fake_prompt)

    resp = test_client.get("/api/new_prompt?debug=true")

    assert resp.status_code == 200
    assert resp.json() == {"prompt": "P", "category": "Test"}
    assert captured["debug"] is True


def test_save_entry_after_refresh(test_client, monkeypatch):
    """Entries saved after fetching a new prompt use that prompt."""

    async def fake_prompt(*, mood=None, energy=None, debug=False):  # pylint: disable=unused-argument
        return {"prompt": "New", "category": "Cat"}

    monkeypatch.setattr(main, "generate_prompt", fake_prompt)

    resp = test_client.get("/api/new_prompt")
    assert resp.status_code == 200
    data = resp.json()

    payload = {
        "date": "2030-01-01",
        "content": "entry",
        "prompt": data["prompt"],
        "category": data["category"],
    }
    resp2 = test_client.post("/entry", json=payload)

    assert resp2.status_code == 200
    text = (main.DATA_DIR / "2030-01-01.md").read_text(encoding="utf-8")
    assert "New" in text


def test_basic_auth_required(monkeypatch):
    """Requests without credentials should be rejected when auth is enabled."""
    monkeypatch.setenv("BASIC_AUTH_USERNAME", "user")
    monkeypatch.setenv("BASIC_AUTH_PASSWORD", "pass")
    import importlib
    import config

    importlib.reload(config)
    mod = importlib.reload(main)
    client = TestClient(mod.app)

    resp = client.get("/")
    assert resp.status_code == 401

    token = base64.b64encode(b"user:pass").decode()
    resp2 = client.get("/", headers={"Authorization": f"Basic {token}"})
    assert resp2.status_code == 200


@pytest.mark.parametrize(
    "header",
    [
        "Basic not_base64",
        f"Basic {base64.b64encode(b'useronly').decode()}",
    ],
)
def test_basic_auth_malformed_headers_logged(monkeypatch, caplog, header):
    """Malformed Basic headers should be rejected and logged."""
    monkeypatch.setenv("BASIC_AUTH_USERNAME", "user")
    monkeypatch.setenv("BASIC_AUTH_PASSWORD", "pass")
    import importlib
    import config

    importlib.reload(config)
    mod = importlib.reload(main)
    client = TestClient(mod.app)

    with caplog.at_level(logging.WARNING, logger="ej.auth"):
        resp = client.get("/", headers={"Authorization": header})
    assert resp.status_code == 401
    assert any(
        "Invalid Basic auth header" in record.getMessage() for record in caplog.records
    )


def test_env_endpoints(test_client, tmp_path, monkeypatch):
    """/api/env returns .env values overridden by settings.yaml and saves updates."""
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=bar\n", encoding="utf-8")
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text("FOO: baz\n", encoding="utf-8")

    import env_utils, settings_utils

    monkeypatch.setattr(env_utils, "ENV_PATH", env_file)
    monkeypatch.setattr(settings_utils, "SETTINGS_PATH", settings_file)
    monkeypatch.setattr(main, "load_env", env_utils.load_env)
    monkeypatch.setattr(main, "load_settings", settings_utils.load_settings)
    monkeypatch.setattr(main, "save_settings", settings_utils.save_settings)

    token = base64.b64encode(b"user:pass").decode()
    resp = test_client.get("/api/env", headers={"Authorization": f"Basic {token}"})
    assert resp.status_code == 200
    # settings.yaml overrides .env
    assert resp.json() == {"FOO": "baz"}

    resp2 = test_client.post(
        "/api/env",
        json={"BAR": "qux"},
        headers={"Authorization": f"Basic {token}"},
    )
    assert resp2.status_code == 200
    body = resp2.json()
    assert body["BAR"] == "qux"
    # Value saved to settings.yaml
    assert "BAR: qux" in settings_file.read_text(encoding="utf-8")


def test_ai_prompt_missing_key(test_client, monkeypatch):
    """AI endpoint returns 503 when API key is missing."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    token = base64.b64encode(b"user:pass").decode()
    resp = test_client.get("/api/ai_prompt", headers={"Authorization": f"Basic {token}"})
    assert resp.status_code == 503


def test_ai_prompt_external_failure(test_client, monkeypatch):
    """AI endpoint returns 503 when external service fails."""
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    async def fake_fetch():
        return None

    monkeypatch.setattr(ai_prompt_utils, "fetch_ai_prompt", fake_fetch)
    token = base64.b64encode(b"user:pass").decode()
    resp = test_client.get("/api/ai_prompt", headers={"Authorization": f"Basic {token}"})
    assert resp.status_code == 503
