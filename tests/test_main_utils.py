"""Tests for helper functions in ``main``."""

# pylint: disable=protected-access

import main


def test_with_updated_save_time_replaces_indented():
    """Existing save_time with indentation should be replaced, not duplicated."""
    fm = "  save_time: Morning\nother: x"
    updated = main._with_updated_save_time(fm, "Evening")
    lines = updated.splitlines()
    assert lines[0] == "  save_time: Evening"
    assert lines[1] == "other: x"
    assert updated.count("save_time:") == 1
