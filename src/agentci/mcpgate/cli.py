from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .checker import CheckResult, check_stdio_server
from .report import write_json_report, write_markdown_report


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="mcpready")
def cli() -> None:
    """CI gate for MCP servers."""


@cli.command()
@click.option(
    "--command",
    "command_line",
    required=True,
    help="Command that starts a stdio MCP server.",
)
@click.option("--timeout", type=float, default=20.0, show_default=True, help="Handshake timeout.")
@click.option("--report", type=click.Path(path_type=Path), help="Write a Markdown report.")
@click.option("--json", "json_path", type=click.Path(path_type=Path), help="Write a JSON report.")
@click.option("--fail-on-warn", is_flag=True, help="Return a non-zero exit code on warnings.")
def check(
    command_line: str,
    timeout: float,
    report: Path | None,
    json_path: Path | None,
    fail_on_warn: bool,
) -> None:
    """Check a stdio MCP server."""

    result = asyncio.run(check_stdio_server(command_line, timeout=timeout))

    if report:
        write_markdown_report(result, report)
    if json_path:
        write_json_report(result, json_path)

    _print_result(result)

    if result.failed or (fail_on_warn and result.warned):
        raise click.exceptions.Exit(1)


def _print_result(result: CheckResult) -> None:
    console = Console()

    table = Table(title="MCPReady")
    table.add_column("Status")
    table.add_column("Tools", justify="right")
    table.add_column("Duration", justify="right")
    table.add_row(result.status, str(len(result.tools)), f"{result.duration_ms}ms")
    console.print(table)

    if result.findings:
        findings = Table(title="Findings")
        findings.add_column("Severity")
        findings.add_column("Code")
        findings.add_column("Target")
        findings.add_column("Message")
        for finding in result.findings:
            findings.add_row(
                finding.severity,
                finding.code,
                finding.target or "",
                finding.message,
            )
        console.print(findings)


if __name__ == "__main__":
    cli()
