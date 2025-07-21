"""Endpoint tests for the Echo Journal application."""

# Disable fixture name shadowing warnings in test functions.
# pytest expects tests to accept the ``test_client`` fixture as an argument,
# which triggers ``redefined-outer-name`` from pylint.
#
# pylint: disable=redefined-outer-name

import os
import shutil
import tempfile
from pathlib import Path

import pytest  # pylint: disable=import-error
from fastapi.testclient import TestClient  # pylint: disable=import-error

# Prepare required directories before importing the app
ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path(tempfile.gettempdir()) / 'ej_app'
STATIC_DIR = APP_DIR / 'static'
PROMPTS_FILE = APP_DIR / 'prompts.json'
DATA_ROOT = Path(tempfile.gettempdir()) / 'ej_journals'

os.environ['APP_DIR'] = str(APP_DIR)
os.environ['DATA_DIR'] = str(DATA_ROOT)
os.environ['STATIC_DIR'] = str(STATIC_DIR)
os.environ['PROMPTS_FILE'] = str(PROMPTS_FILE)

STATIC_DIR.mkdir(parents=True, exist_ok=True)
DATA_ROOT.mkdir(parents=True, exist_ok=True)
# copy prompts file if not already
if not PROMPTS_FILE.exists():
    shutil.copy(ROOT / 'prompts.json', PROMPTS_FILE)

# Import the application after environment setup
import main  # type: ignore  # pylint: disable=wrong-import-position


@pytest.fixture()
def test_client(tmp_path, monkeypatch):
    """Return a TestClient instance using a temporary journals directory."""
    journals = tmp_path / 'journals'
    journals.mkdir()
    monkeypatch.setattr(main, 'DATA_DIR', journals)
    return TestClient(main.app)


def test_index_returns_page(test_client):
    """Requesting the index should return the journal page."""
    resp = test_client.get('/')
    assert resp.status_code == 200
    assert 'Echo Journal' in resp.text


def test_save_entry_and_retrieve(test_client):
    """Entries can be saved and later retrieved."""
    payload = {'date': '2020-01-01', 'content': 'entry', 'prompt': 'prompt'}
    resp = test_client.post('/entry', json=payload)
    assert resp.status_code == 200
    assert resp.json()['status'] == 'success'
    file_path = main.DATA_DIR / '2020-01-01.md'
    assert file_path.exists()
    resp2 = test_client.get('/entry/2020-01-01')
    assert resp2.status_code == 200
    assert 'prompt' in resp2.json()['content']


def test_save_entry_missing_fields(test_client):
    """Saving with missing required fields should return an error."""
    resp = test_client.post('/entry', json={'date': '2020-01-02'})
    assert resp.status_code == 200
    assert resp.json()['status'] == 'error'


def test_get_entry_not_found(test_client):
    """Fetching a non-existent entry should return 404."""
    resp = test_client.get('/entry/1999-01-01')
    assert resp.status_code == 404


def test_load_entry(test_client):
    """load_entry endpoint should return the entry text without headers."""
    (main.DATA_DIR / '2020-02-02.md').write_text('# Prompt\nA\n\n# Entry\nB', encoding='utf-8')
    resp = test_client.get('/entry', params={'entry_date': '2020-02-02'})
    assert resp.status_code == 200
    assert resp.json()['content'] == 'B'


def test_load_entry_missing(test_client):
    """Loading a missing entry should return 404."""
    resp = test_client.get('/entry', params={'entry_date': '2000-01-01'})
    assert resp.status_code == 404


def test_view_entry_existing(test_client):
    """Existing entries can be viewed in read-only mode."""
    (main.DATA_DIR / '2020-03-03.md').write_text('# Prompt\nA\n\n# Entry\nB', encoding='utf-8')
    resp = test_client.get('/view/2020-03-03')
    assert resp.status_code == 200
    assert 'B' in resp.text
    assert 'readonly' in resp.text


def test_view_entry_multiline_prompt(test_client):
    """Prompts spanning multiple lines should render correctly."""
    content = '# Prompt\nLine1\nLine2\n\n# Entry\nBody'
    (main.DATA_DIR / '2020-03-04.md').write_text(content, encoding='utf-8')
    resp = test_client.get('/view/2020-03-04')
    assert resp.status_code == 200
    assert 'Line1' in resp.text and 'Line2' in resp.text
    assert 'Body' in resp.text


def test_view_entry_malformed(test_client):
    """Malformed files trigger a server error."""
    (main.DATA_DIR / 'bad.md').write_text('No headings here', encoding='utf-8')
    resp = test_client.get('/view/bad')
    assert resp.status_code == 500


def test_view_entry_missing(test_client):
    """Requesting a missing entry by date returns 404."""
    resp = test_client.get('/view/2020-04-04')
    assert resp.status_code == 404


def test_archive_view(test_client):
    """The archive page lists all valid entries."""
    (main.DATA_DIR / '2020-05-01.md').write_text('# Prompt\nP\n\n# Entry\nE1', encoding='utf-8')
    (main.DATA_DIR / '2020-05-02.md').write_text('# Prompt\nP\n\n# Entry\nE2', encoding='utf-8')
    (main.DATA_DIR / 'badfile.md').write_text('oops', encoding='utf-8')
    subdir = main.DATA_DIR / '2021'
    subdir.mkdir()
    (subdir / '2021-06-01.md').write_text('# Prompt\nP\n\n# Entry\nE3', encoding='utf-8')
    resp = test_client.get('/archive')
    assert resp.status_code == 200
    assert '2020-05-01' in resp.text
    assert '2020-05-02' in resp.text
    assert '2021-06-01' in resp.text
    assert 'badfile' not in resp.text

def test_save_entry_invalid_date(test_client):
    """Entries with malformed date strings are still saved as-is."""
    payload = {'date': '2020-13-40', 'content': 'bad', 'prompt': 'p'}
    resp = test_client.post('/entry', json=payload)
    assert resp.status_code == 200
    assert resp.json()['status'] == 'success'
    assert (main.DATA_DIR / '2020-13-40.md').exists()


def test_save_entry_path_traversal(test_client):
    """Attempting directory traversal should only affect paths inside DATA_DIR."""
    malicious = '../malicious'
    payload = {'date': malicious, 'content': 'x', 'prompt': 'y'}
    resp = test_client.post('/entry', json=payload)
    assert resp.status_code == 200
    expected = main.DATA_DIR / 'malicious.md'
    assert expected.exists()
    assert expected.resolve().is_relative_to(main.DATA_DIR.resolve())


def test_get_entry_invalid_date(test_client):
    """Invalid date segments should yield a 404 response."""
    resp = test_client.get('/entry/invalid-date')
    assert resp.status_code == 404


def test_view_entry_traversal(test_client):
    """Path traversal attempts in view routes should be denied."""
    resp = test_client.get('/view/../../etc/passwd')
    assert resp.status_code == 404
