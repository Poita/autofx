import sys

import autofx.editor_server
from autofx import cli


def run_main(monkeypatch, argv):
    calls = []
    monkeypatch.setattr(autofx.editor_server, "run_editor",
                        lambda *args, **kwargs: calls.append((args, kwargs)) or 0)
    monkeypatch.setattr(sys, "argv", ["autofx", *argv])
    assert cli.main() == 0
    return calls


def test_editor_subcommand_defaults(monkeypatch):
    calls = run_main(monkeypatch, ["editor"])
    assert calls == [((".",), {"port": 8765, "open_browser": True})]


def test_editor_subcommand_options(monkeypatch):
    calls = run_main(monkeypatch, ["editor", "examples/fire.glsl", "--port", "9000", "--no-browser"])
    assert calls == [(("examples/fire.glsl",), {"port": 9000, "open_browser": False})]
