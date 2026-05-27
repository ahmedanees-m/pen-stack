"""Version test for pen-stack.compare (migrated from pen-compare v0.1.0)."""
import pen_stack.compare
from pen_stack.compare._version import __version__ as compare_version
import pen_stack


def test_compare_version_string():
    """pen_stack.compare keeps its own version for citation/compatibility."""
    assert compare_version == "0.1.0"


def test_penstack_version_importable():
    assert pen_stack.__version__ == "1.0.0a1"
