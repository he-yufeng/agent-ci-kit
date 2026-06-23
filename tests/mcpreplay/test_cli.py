from __future__ import annotations

import sys
from pathlib import Path

from click.testing import CliRunner

from agentci.mcpreplay.cli import main


def test_cli_record_inspect_redact_and_replay(tmp_path):
    runner = CliRunner()
    server = _write_server(tmp_path)
    command = f'"{sys.executable}" "{server}"'
    transcript = tmp_path / "transcript.jsonl"
    redacted = tmp_path / "safe.jsonl"

    result = runner.invoke(main, ["record", "--command", command, "--out", str(transcript)])
    assert result.exit_code == 0, result.output
    assert transcript.exists()

    result = runner.invoke(main, ["inspect", str(transcript), "--format", "md"])
    assert result.exit_code == 0, result.output
    assert "MCPReplay Report" in result.output
    assert "tools/list" in result.output

    result = runner.invoke(main, ["redact", str(transcript), "--out", str(redacted)])
    assert result.exit_code == 0, result.output
    assert redacted.exists()

    result = runner.invoke(main, ["replay", str(redacted), "--command", command])
    assert result.exit_code == 0, result.output
    assert "Replay matched" in result.output


def _write_server(tmp_path: Path) -> Path:
    path = tmp_path / "server.py"
    path.write_text(
        """
import json
import sys

for line in sys.stdin:
    message = json.loads(line)
    if "id" not in message:
        continue
    if message.get("method") == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {}}
    else:
        result = {"tools": [{"name": "echo", "description": "Echo text"}]}
    print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
""",
        encoding="utf-8",
    )
    return path
