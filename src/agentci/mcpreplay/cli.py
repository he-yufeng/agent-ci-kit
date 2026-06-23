from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from .replay import ReplayMismatch, replay_transcript
from .report import render_json, render_markdown
from .stdio import default_probe_messages, record_stdio
from .transcript import load_transcript, redact_transcript, save_transcript

console = Console()


@click.group()
def main() -> None:
    """Record and replay MCP JSON-RPC transcripts."""


@main.command()
@click.option("--command", "server_command", required=True, help="MCP server command to run.")
@click.option(
    "--out",
    "output",
    required=True,
    type=click.Path(path_type=Path),
    help="JSONL output.",
)
@click.option(
    "--messages",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Optional JSON file containing a list of client messages.",
)
def record(server_command: str, output: Path, messages: Path | None) -> None:
    """Record stdio MCP responses for a client message sequence."""
    client_messages = _load_messages(messages) if messages else default_probe_messages()
    events = record_stdio(server_command, client_messages)
    save_transcript(events, output)
    console.print(f"Recorded {len(events)} events to {output}")


@main.command()
@click.argument("transcript", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--command", "server_command", required=True, help="MCP server command to run.")
def replay(transcript: Path, server_command: str) -> None:
    """Replay client messages and compare server responses."""
    events = load_transcript(transcript)
    try:
        notes = replay_transcript(events, server_command)
    except ReplayMismatch as exc:
        console.print(f"[red]Replay mismatch:[/] {exc}")
        raise click.ClickException(exc.reason) from exc
    for note in notes:
        console.print(note)
    console.print("[green]Replay matched transcript shape.[/]")


@main.command(name="inspect")
@click.argument("transcript", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--format", "fmt", type=click.Choice(["md", "json"]), default="md", show_default=True)
def inspect_cmd(transcript: Path, fmt: str) -> None:
    """Print a transcript report."""
    events = load_transcript(transcript)
    console.print(render_json(events) if fmt == "json" else render_markdown(events))


@main.command()
@click.argument("transcript", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--out",
    "output",
    required=True,
    type=click.Path(path_type=Path),
    help="Redacted JSONL.",
)
def redact(transcript: Path, output: Path) -> None:
    """Redact common credentials from a transcript."""
    events = load_transcript(transcript)
    safe_events = redact_transcript(events)
    save_transcript(safe_events, output)
    console.print(f"Wrote redacted transcript to {output}")


def _load_messages(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return default_probe_messages()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise click.ClickException("--messages must contain a JSON array of objects")
    return data


if __name__ == "__main__":
    main()
