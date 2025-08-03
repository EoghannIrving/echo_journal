"""Tests for prompt utility helpers."""

import asyncio

import prompt_utils

# pylint: disable=protected-access


def test_generate_prompt_filters_and_category(tmp_path, monkeypatch):
    """generate_prompt respects mood/energy filters and derives categories."""
    content = (
        "- id: cat-001\n"
        "  prompt: 'A'\n"
        "  tags:\n    - alpha\n"
        "  energy: 3\n"
        "  mood: ok\n"
        "- id: dog_001\n"
        "  prompt: 'B'\n"
        "  tags:\n    - beta\n"
        "  energy: 1\n"
        "  mood: ok\n"
    )
    pfile = tmp_path / "prompts.yaml"
    pfile.write_text(content, encoding="utf-8")
    monkeypatch.setattr(prompt_utils, "PROMPTS_FILE", pfile)
    prompt_utils._prompts_cache = {"data": None, "mtime": None}

    res = asyncio.run(prompt_utils.generate_prompt(mood="ok", energy=2))

    assert res["prompt"] == "B"
    assert res["category"] == "Dog"
    assert res["tags"] == ["beta"]


def test_generate_prompt_debug(tmp_path, monkeypatch):
    """generate_prompt returns debug info when requested."""
    content = (
        "- id: cat-001\n"
        "  prompt: 'A'\n"
        "  mood: ok\n"
        "  energy: 5\n"
        "- id: dog_001\n"
        "  prompt: 'B'\n"
        "  mood: ok\n"
        "  energy: 1\n"
    )
    pfile = tmp_path / "prompts.yaml"
    pfile.write_text(content, encoding="utf-8")
    monkeypatch.setattr(prompt_utils, "PROMPTS_FILE", pfile)
    prompt_utils._prompts_cache = {"data": None, "mtime": None}

    res = asyncio.run(prompt_utils.generate_prompt(mood="ok", energy=1, debug=True))

    assert res["id"] == "dog_001"
    assert res["debug"]["initial"] == ["cat-001", "dog_001"]
    assert res["debug"]["after_energy"] == ["dog_001"]
