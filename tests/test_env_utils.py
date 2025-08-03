"""Tests for ``env_utils`` helpers."""

import logging

from echo_journal import env_utils


def test_load_env_parses_pairs(tmp_path):
    """Key=value pairs should be returned ignoring comments and invalid lines."""
    p = tmp_path / "test.env"
    p.write_text("A=1\n#comment\nB=two\ninvalid\n", encoding="utf-8")
    env = env_utils.load_env(p)
    assert env == {"A": "1", "B": "two"}


def test_load_env_logs_error(tmp_path, caplog):
    """Missing files should log an error and return an empty dict."""
    p = tmp_path / "missing.env"
    with caplog.at_level(logging.ERROR, logger="ej.env"):
        env = env_utils.load_env(p)
    assert not env
    assert any(str(p) in r.getMessage() for r in caplog.records)
