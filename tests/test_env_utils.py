"""Tests for ``env_utils`` helpers."""

import importlib
import logging

from echo_journal import env_utils


def test_load_env_parses_pairs(tmp_path):
    """Key=value pairs should be returned ignoring comments and invalid lines."""
    p = tmp_path / "test.env"
    p.write_text("A=1\n#comment\nB=two\ninvalid\n", encoding="utf-8")
    env = env_utils.load_env(p)
    assert env == {"A": "1", "B": "two"}


def test_load_env_handles_quotes_and_equals(tmp_path):
    """Quoted values and additional ``=`` characters should be parsed."""
    p = tmp_path / "quoted.env"
    p.write_text('A="hello world"\nB=foo=bar\nC="x=y"\n', encoding="utf-8")
    env = env_utils.load_env(p)
    assert env == {"A": "hello world", "B": "foo=bar", "C": "x=y"}


def test_load_env_logs_error(tmp_path, caplog):
    """Missing files should log an error and return an empty dict."""
    p = tmp_path / "missing.env"
    with caplog.at_level(logging.ERROR, logger="ej.env"):
        env = env_utils.load_env(p)
    assert not env
    assert any(str(p) in r.getMessage() for r in caplog.records)


def test_load_env_from_alternate_cwd(tmp_path, monkeypatch):
    """Default ``ENV_PATH`` should work regardless of the current directory."""
    env_file = tmp_path / "alt.env"
    env_file.write_text("A=1\n", encoding="utf-8")
    monkeypatch.setenv("ECHO_JOURNAL_ENV_PATH", str(env_file))
    importlib.reload(env_utils)
    subdir = tmp_path / "sub"
    subdir.mkdir()
    monkeypatch.chdir(subdir)
    assert env_utils.load_env() == {"A": "1"}
    monkeypatch.delenv("ECHO_JOURNAL_ENV_PATH", raising=False)
    importlib.reload(env_utils)
