from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner

from agentci.mcpgate.cli import cli

FIXTURES = Path(__file__).parent / "fixtures"


def command_for(name: str) -> str:
    return f'"{sys.executable}" "{FIXTURES / name}"'


def test_cli_writes_reports(tmp_path: Path) -> None:
    markdown = tmp_path / "report.md"
    json_report = tmp_path / "report.json"

    result = CliRunner().invoke(
        cli,
        [
            "check",
            "--command",
            command_for("good_server.py"),
            "--report",
            str(markdown),
            "--json",
            str(json_report),
        ],
    )

    assert result.exit_code == 0
    assert "passed" in result.output
    assert "MCPReady Report" in markdown.read_text(encoding="utf-8")
    assert json.loads(json_report.read_text(encoding="utf-8"))["status"] == "passed"


def test_cli_can_fail_on_warnings() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "check",
            "--command",
            command_for("empty_server.py"),
            "--fail-on-warn",
        ],
    )

    assert result.exit_code == 1
    assert "no_tools" in result.output
