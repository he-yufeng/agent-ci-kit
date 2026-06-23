from __future__ import annotations

import json

from click.testing import CliRunner

from agentci.toolfence.cli import main


def test_init_and_run_default_fixtures() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        init_result = runner.invoke(main, ["init"])
        assert init_result.exit_code == 0

        run_result = runner.invoke(main, ["run", "tests/toolfence/read-only-ok.yaml"])
        assert run_result.exit_code == 0

        with open(".toolfence/results.json", encoding="utf-8") as result_file:
            payload = json.loads(result_file.read())
        assert payload["passed"] is True
        assert payload["total"] == 1


def test_run_exits_nonzero_for_blocked_fixture() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["run", "tests/toolfence/blocked-shell.yaml"])
        assert result.exit_code == 1


def test_allowed_tools_reject_unlisted_calls() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        fixture = {
            "name": "allow-list",
            "tools": [{"name": "docs.search"}, {"name": "shell.run", "risk": "dangerous"}],
            "transcript": [
                {
                    "role": "assistant",
                    "tool_calls": [{"name": "shell.run", "arguments": {"cmd": "whoami"}}],
                }
            ],
            "expect": {"allowed": ["docs.search"]},
        }
        with open("allow-list.json", "w", encoding="utf-8") as fixture_file:
            json.dump(fixture, fixture_file)

        result = runner.invoke(main, ["run", "allow-list.json", "-o", "results.json"])

        assert result.exit_code == 1
        with open("results.json", encoding="utf-8") as result_file:
            payload = json.loads(result_file.read())
        assert payload["finding_summary"] == {"unexpected-tool-called": 1}
        assert payload["results"][0]["findings"][0]["rule"] == "unexpected-tool-called"


def test_report_renders_markdown() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init"])
        runner.invoke(main, ["run", "tests/toolfence/read-only-ok.yaml"])

        result = runner.invoke(main, ["report"])
        assert result.exit_code == 0
        assert "Agent ToolFence Report" in result.output


def test_report_includes_finding_summary() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init"])
        runner.invoke(main, ["run", "tests/toolfence/blocked-shell.yaml"])

        result = runner.invoke(main, ["report"])

        assert result.exit_code == 0
        assert "Finding Summary" in result.output
        assert "`missing-confirmation`" in result.output
