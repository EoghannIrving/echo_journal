import shutil
from pathlib import Path
import importlib

import pytest
from fastapi.testclient import TestClient

# Prepare required directories before importing the app
ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path('/app')
STATIC_DIR = APP_DIR / 'static'
PROMPTS_FILE = APP_DIR / 'prompts.json'
DATA_ROOT = Path('/journals')

STATIC_DIR.mkdir(parents=True, exist_ok=True)
DATA_ROOT.mkdir(parents=True, exist_ok=True)
# copy prompts file if not already
if not PROMPTS_FILE.exists():
    shutil.copy(ROOT / 'prompts.json', PROMPTS_FILE)

# Import the application after environment setup
import main  # type: ignore


@pytest.fixture()
def client(tmp_path, monkeypatch):
    journals = tmp_path / 'journals'
    journals.mkdir()
    monkeypatch.setattr(main, 'DATA_DIR', journals)
    return TestClient(main.app)


def test_index_returns_page(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert 'Echo Journal' in resp.text


def test_save_entry_and_retrieve(client):
    payload = {'date': '2020-01-01', 'content': 'entry', 'prompt': 'prompt'}
    resp = client.post('/entry', json=payload)
    assert resp.status_code == 200
    assert resp.json()['status'] == 'success'
    file_path = main.DATA_DIR / '2020-01-01.md'
    assert file_path.exists()
    resp2 = client.get('/entry/2020-01-01')
    assert resp2.status_code == 200
    assert 'prompt' in resp2.json()['content']


def test_save_entry_missing_fields(client):
    resp = client.post('/entry', json={'date': '2020-01-02'})
    assert resp.status_code == 200
    assert resp.json()['status'] == 'error'


def test_get_entry_not_found(client):
    resp = client.get('/entry/1999-01-01')
    assert resp.status_code == 404


def test_load_entry(client):
    (main.DATA_DIR / '2020-02-02.md').write_text('# Prompt\nA\n\n# Entry\nB', encoding='utf-8')
    resp = client.get('/entry', params={'entry_date': '2020-02-02'})
    assert resp.status_code == 200
    assert resp.json()['content'] == 'B'


def test_load_entry_missing(client):
    resp = client.get('/entry', params={'entry_date': '2000-01-01'})
    assert resp.status_code == 404


def test_view_entry_existing(client):
    (main.DATA_DIR / '2020-03-03.md').write_text('# Prompt\nA\n\n# Entry\nB', encoding='utf-8')
    resp = client.get('/view/2020-03-03')
    assert resp.status_code == 200
    assert 'B' in resp.text
    assert 'readonly' in resp.text


def test_view_entry_missing(client):
    resp = client.get('/view/2020-04-04')
    assert resp.status_code == 404


def test_archive_view(client):
    (main.DATA_DIR / '2020-05-01.md').write_text('# Prompt\nP\n\n# Entry\nE1', encoding='utf-8')
    (main.DATA_DIR / '2020-05-02.md').write_text('# Prompt\nP\n\n# Entry\nE2', encoding='utf-8')
    (main.DATA_DIR / 'badfile.md').write_text('oops', encoding='utf-8')
    subdir = main.DATA_DIR / '2021'
    subdir.mkdir()
    (subdir / '2021-06-01.md').write_text('# Prompt\nP\n\n# Entry\nE3', encoding='utf-8')
    resp = client.get('/archive')
    assert resp.status_code == 200
    assert '2020-05-01' in resp.text
    assert '2020-05-02' in resp.text
    assert '2021-06-01' in resp.text
    assert 'badfile' not in resp.text

def test_save_entry_invalid_date(client):
    """Entries with malformed date strings are still saved as-is."""
    payload = {'date': '2020-13-40', 'content': 'bad', 'prompt': 'p'}
    resp = client.post('/entry', json=payload)
    assert resp.status_code == 200
    assert resp.json()['status'] == 'success'
    assert (main.DATA_DIR / '2020-13-40.md').exists()


def test_save_entry_path_traversal(client):
    """Attempting directory traversal should only affect paths inside DATA_DIR."""
    malicious = '../malicious'
    payload = {'date': malicious, 'content': 'x', 'prompt': 'y'}
    resp = client.post('/entry', json=payload)
    assert resp.status_code == 200
    expected = main.DATA_DIR / 'malicious.md'
    assert expected.exists()
    assert expected.resolve().is_relative_to(main.DATA_DIR.resolve())


def test_get_entry_invalid_date(client):
    resp = client.get('/entry/invalid-date')
    assert resp.status_code == 404


def test_view_entry_traversal(client):
    resp = client.get('/view/../../etc/passwd')
    assert resp.status_code == 404
