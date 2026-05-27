"""Unit tests for pen_compare.cli."""

from click.testing import CliRunner

from pen_stack.compare.cli import main


def test_main_no_args_shows_help():
    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert "PEN-COMPARE" in result.output


def test_version_option():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_compare_command():
    runner = CliRunner()
    result = runner.invoke(main, ["compare", "ISCro4", "IS621"])
    assert result.exit_code == 0
    assert "ISCro4" in result.output
    assert "IS621" in result.output


def test_list_writers_command():
    runner = CliRunner()
    result = runner.invoke(main, ["list-writers"])
    assert result.exit_code == 0
    assert "TRUE_WRITER" in result.output


def test_help_flag():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "compare" in result.output
    assert "list-writers" in result.output
