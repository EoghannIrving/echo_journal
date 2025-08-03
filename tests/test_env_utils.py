"""Tests for ``env_utils`` helpers."""

import logging

import env_utils


def test_load_env_parses_pairs(tmp_path):
    """Key=value pairs should be returned ignoring comments and invalid lines."""
    p = tmp_path / "test.env"
    p.write_text("A=1\n#comment\nB=two\ninvalid\n", encoding="utf-8")
    env = env_utils.load_env(p)
    assert env == {"A": "1", "B": "two"}


def test_save_env_merges_and_writes(tmp_path):
    """``save_env`` should merge values and write them to disk."""
    p = tmp_path / "test.env"
    p.write_text("A=1\n", encoding="utf-8")
    data = env_utils.save_env({"B": "2"}, p)
    assert data == {"A": "1", "B": "2"}
    assert p.read_text(encoding="utf-8") == "A=1\nB=2\n"


def test_load_env_logs_error(tmp_path, caplog):
    """Missing files should log an error and return an empty dict."""
    p = tmp_path / "missing.env"
    with caplog.at_level(logging.ERROR, logger="ej.env"):
        env = env_utils.load_env(p)
    assert env == {}
    assert any(str(p) in r.getMessage() for r in caplog.records)


def test_save_env_logs_error(tmp_path, caplog):
    """Errors writing .env files should be logged."""
    p = tmp_path / "dir" / "test.env"
    with caplog.at_level(logging.ERROR, logger="ej.env"):
        data = env_utils.save_env({"A": "1"}, p)
    assert data == {"A": "1"}
    assert any(str(p) in r.getMessage() for r in caplog.records)
