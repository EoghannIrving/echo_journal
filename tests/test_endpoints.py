"""Endpoint tests for the Echo Journal application."""

# Disable fixture name shadowing warnings in test functions.
# pytest expects tests to accept the ``test_client`` fixture as an argument,
# which triggers ``redefined-outer-name`` from pylint.
#
# pylint: disable=redefined-outer-name

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import aiofiles  # type: ignore  # pylint: disable=import-error
import pytest  # pylint: disable=import-error
from fastapi.testclient import TestClient  # pylint: disable=import-error

# Prepare required directories before importing the app
ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path(tempfile.gettempdir()) / "ej_app"
STATIC_DIR = APP_DIR / "static"
PROMPTS_FILE = APP_DIR / "prompts.json"
DATA_ROOT = Path(tempfile.gettempdir()) / "ej_journals"

os.environ["APP_DIR"] = str(APP_DIR)
os.environ["DATA_DIR"] = str(DATA_ROOT)
os.environ["STATIC_DIR"] = str(STATIC_DIR)
os.environ["PROMPTS_FILE"] = str(PROMPTS_FILE)

# Ensure directories for the application exist before importing ``main``
STATIC_DIR.mkdir(parents=True, exist_ok=True)
DATA_ROOT.mkdir(parents=True, exist_ok=True)
# copy prompts file if not already
if not PROMPTS_FILE.exists():
    shutil.copy(ROOT / "prompts.json", PROMPTS_FILE)

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
        return "serendipity"

    monkeypatch.setattr(weather_utils, "fetch_word_of_day", fake_word)
    payload = {"date": "2020-10-10", "content": "entry", "prompt": "prompt"}
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    text = (main.DATA_DIR / "2020-10-10.md").read_text(encoding="utf-8")
    assert "wotd: serendipity" in text


def test_save_entry_missing_fields(test_client):
    """Saving with missing required fields should return an error."""
    resp = test_client.post("/entry", json={"date": "2020-01-02"})
    assert resp.status_code == 200
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
    """Malformed files are displayed as plain text without error."""
    (main.DATA_DIR / "bad.md").write_text("No headings here", encoding="utf-8")
    resp = test_client.get("/archive/bad")
    assert resp.status_code == 200
    assert "No headings here" in resp.text


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
    assert "badfile" not in resp.text


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
    """Entries with malformed date strings are still saved as-is."""
    payload = {"date": "2020-13-40", "content": "bad", "prompt": "p"}
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert (main.DATA_DIR / "2020-13-40.md").exists()


def test_save_entry_path_traversal(test_client):
    """Attempting directory traversal should only affect paths inside DATA_DIR."""
    malicious = "../malicious"
    payload = {"date": malicious, "content": "x", "prompt": "y"}
    resp = test_client.post("/entry", json=payload)
    assert resp.status_code == 200
    expected = main.DATA_DIR / "malicious.md"
    assert expected.exists()
    assert expected.resolve().is_relative_to(main.DATA_DIR.resolve())


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
    entry3 = (
        """---
location: Atown
photos: []
---
# Prompt
P3

# Entry
E3"""
    )
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
    content = (
        """---
wotd: luminous
photos: []
---
# Prompt
P

# Entry
E"""
    )
    (main.DATA_DIR / "2021-08-01.md").write_text(content, encoding="utf-8")
    resp = test_client.get("/archive/2021-08-01")
    assert resp.status_code == 200
    assert "luminous" in resp.text


def test_archive_shows_wotd_icon(test_client):
    """Entries with a word of the day show an icon in the archive."""
    content = (
        """---
wotd: zephyr
photos: []
---
# Prompt
P

# Entry
E"""
    )
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
