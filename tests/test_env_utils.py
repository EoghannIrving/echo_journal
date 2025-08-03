"""Tests for ``env_utils`` helpers."""

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
