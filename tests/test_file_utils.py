"""Tests for file utilities."""

from echo_journal import file_utils


def test_parse_entry_preserves_trailing_newlines():
    """``parse_entry`` should keep trailing newlines in the entry."""
    md = "# Prompt\nP\n\n# Entry\nLine\n\n"
    prompt, entry = file_utils.parse_entry(md)
    assert prompt == "P\n"
    assert entry == "Line\n"


def test_parse_frontmatter_simple_pairs():
    """Simple key/value YAML should be parsed into a dictionary."""
    fm = "location: Testville\nweather: Warm"
    meta = file_utils.parse_frontmatter(fm)
    assert meta["location"] == "Testville"
    assert meta["weather"] == "Warm"


def test_parse_frontmatter_list_values():
    """YAML lists should be returned as Python lists."""
    fm = "photos:\n  - img1.jpg\n  - img2.jpg\n"
    meta = file_utils.parse_frontmatter(fm)
    assert meta["photos"] == ["img1.jpg", "img2.jpg"]


def test_parse_frontmatter_invalid_returns_empty():
    """Malformed YAML should result in an empty dict."""
    fm = "bad: [unclosed"
    meta = file_utils.parse_frontmatter(fm)
    assert meta == {}


def test_weather_description_includes_temp():
    """``weather_description`` should include condition and temperature."""
    assert file_utils.weather_description("12°C code 1") == "Mostly clear, 12°C"
