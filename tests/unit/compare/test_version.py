"""Basic import and version test for pen-compare scaffolding (Step 1)."""

import pen_stack.compare


def test_version_string():
    assert pen_compare.__version__ == "0.1.0"


def test_version_importable():
    from pen_stack.compare._version import __version__

    assert __version__ == "0.1.0"
