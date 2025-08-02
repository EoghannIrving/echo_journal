import asyncio

import prompt_utils


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
