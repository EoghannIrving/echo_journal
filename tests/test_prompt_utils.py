"""Tests for prompt utility helpers."""

import asyncio

from echo_journal import prompt_utils

# pylint: disable=protected-access


def test_generate_prompt_uses_anchor(tmp_path, monkeypatch):
    """generate_prompt selects prompts based on derived anchor."""
    content = (
        "- id: cat-001\n"
        "  prompt: 'A'\n"
        "  tags:\n    - alpha\n"
        "  mood: meh\n"
        "  energy: 1\n"
        "  anchor: soft\n"
        "- id: dog_001\n"
        "  prompt: 'B'\n"
        "  tags:\n    - beta\n"
        "  mood: joyful\n"
        "  energy: 4\n"
        "  anchor: strong\n"
    )
    pfile = tmp_path / "prompts.yaml"
    pfile.write_text(content, encoding="utf-8")
    monkeypatch.setattr(prompt_utils, "PROMPTS_FILE", pfile)
    prompt_utils._prompts_cache = {"data": None, "mtime": None}
    monkeypatch.setattr(prompt_utils.random, "choice", lambda seq: seq[0])

    res = asyncio.run(prompt_utils.generate_prompt(mood="meh", energy=2))

    assert res["prompt"] == "A"
    assert res["category"] == "Cat"
    assert res["tags"] == ["alpha"]
    assert res["anchor"] == "soft"


def test_generate_prompt_debug(tmp_path, monkeypatch):
    """generate_prompt returns debug info with anchor filtering."""
    content = (
        "- id: cat-001\n"
        "  prompt: 'A'\n"
        "  mood: meh\n"
        "  energy: 5\n"
        "  anchor: soft\n"
        "- id: dog_001\n"
        "  prompt: 'B'\n"
        "  mood: meh\n"
        "  energy: 1\n"
        "  anchor: soft\n"
    )
    pfile = tmp_path / "prompts.yaml"
    pfile.write_text(content, encoding="utf-8")
    monkeypatch.setattr(prompt_utils, "PROMPTS_FILE", pfile)
    prompt_utils._prompts_cache = {"data": None, "mtime": None}
    monkeypatch.setattr(prompt_utils.random, "choice", lambda seq: seq[0])

    res = asyncio.run(prompt_utils.generate_prompt(mood="meh", energy=2, debug=True))

    assert res["id"] == "cat-001"
    assert res["debug"]["initial"] == ["cat-001", "dog_001"]
    assert res["debug"]["after_anchor"] == ["cat-001", "dog_001"]
    assert res["debug"]["chosen"] == "cat-001"
    assert set(res["debug"].keys()) == {"initial", "after_anchor", "chosen"}


def test_choose_anchor_self_doubt(monkeypatch):
    """_choose_anchor prioritizes micro for self-doubt."""
    monkeypatch.setattr(prompt_utils.random, "choice", lambda seq: seq[0])
    assert prompt_utils._choose_anchor("self-doubt", 2) == "micro"


def test_choose_anchor_joyful_high_energy(monkeypatch):
    """_choose_anchor can return strong for joyful mood."""
    monkeypatch.setattr(prompt_utils.random, "choice", lambda seq: seq[-1])
    assert prompt_utils._choose_anchor("joyful", 3) == "strong"
