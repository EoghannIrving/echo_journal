import file_utils


def test_parse_entry_preserves_trailing_newlines():
    md = "# Prompt\nP\n\n# Entry\nLine\n\n"
    prompt, entry = file_utils.parse_entry(md)
    assert prompt == "P\n"
    assert entry == "Line\n"

