"""Tiny smoke tests runnable on the laptop (no GPU, no upstream data)."""
import importlib

import pen_stack


def test_version():
    # don't pin the exact version (it bumps per phase/cycle) - just assert it's a valid released-series string
    assert pen_stack.__version__.split(".")[0] in {"3", "4", "5", "6"}


def test_all_modules_import():
    for m in ["atlas", "mech", "score", "wgenome", "planner", "bridge",
              "monitor", "rag", "agent", "ui", "data", "validate", "server"]:
        importlib.import_module(f"pen_stack.{m}")


def test_cli_info(capsys):
    from click.testing import CliRunner
    from pen_stack.cli import main

    res = CliRunner().invoke(main, ["info"])
    assert res.exit_code == 0
    assert "PEN-STACK" in res.output
