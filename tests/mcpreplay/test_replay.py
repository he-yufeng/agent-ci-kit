from __future__ import annotations

import sys
from pathlib import Path

import pytest

from agentci.mcpreplay.replay import ReplayMismatch, replay_transcript
from agentci.mcpreplay.stdio import record_stdio
from agentci.mcpreplay.transcript import TranscriptEvent


def test_record_and_replay_stdio_server(tmp_path):
    server = _write_server(tmp_path, include_tools=True)
    command = _python_command(server)

    events = record_stdio(command)
    assert [event.direction for event in events] == [
        "client",
        "server",
        "client",
        "client",
        "server",
    ]

    notes = replay_transcript(events, command)
    assert notes[-1] == "client event 4: response 2 matched"


def test_replay_detects_missing_result_key(tmp_path):
    server = _write_server(tmp_path, include_tools=False)
    command = _python_command(server)
    transcript = [
        TranscriptEvent(
            seq=1,
            direction="client",
            message={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        ),
        TranscriptEvent(
            seq=2,
            direction="server",
            message={"jsonrpc": "2.0", "id": 1, "result": {"tools": []}},
        ),
    ]

    with pytest.raises(ReplayMismatch, match="result missing keys"):
        replay_transcript(transcript, command)


def test_replay_matches_notification_before_response(tmp_path):
    server = _write_server(tmp_path, include_tools=True, notify_before_tools=True)
    command = _python_command(server)
    transcript = [
        TranscriptEvent(
            seq=1,
            direction="client",
            message={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        ),
        TranscriptEvent(
            seq=2,
            direction="server",
            message={
                "jsonrpc": "2.0",
                "method": "notifications/tools/list_changed",
                "params": {"reason": "startup"},
            },
        ),
        TranscriptEvent(
            seq=3,
            direction="server",
            message={"jsonrpc": "2.0", "id": 1, "result": {"tools": []}},
        ),
    ]

    notes = replay_transcript(transcript, command)

    assert notes == [
        "server event 2: notification 'notifications/tools/list_changed' matched",
        "client event 1: response 1 matched",
    ]


def test_replay_detects_unexpected_notification_method(tmp_path):
    server = _write_server(tmp_path, include_tools=True, notify_before_tools=True)
    command = _python_command(server)
    transcript = [
        TranscriptEvent(
            seq=1,
            direction="client",
            message={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        ),
        TranscriptEvent(
            seq=2,
            direction="server",
            message={"jsonrpc": "2.0", "method": "notifications/resources/list_changed"},
        ),
        TranscriptEvent(
            seq=3,
            direction="server",
            message={"jsonrpc": "2.0", "id": 1, "result": {"tools": []}},
        ),
    ]

    with pytest.raises(ReplayMismatch, match="notification method mismatch"):
        replay_transcript(transcript, command)


def _write_server(
    tmp_path: Path,
    *,
    include_tools: bool,
    notify_before_tools: bool = False,
) -> Path:
    result = '{"tools": []}' if include_tools else "{}"
    notification = (
        """
        print(json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/tools/list_changed",
            "params": {"reason": "startup"},
        }), flush=True)
"""
        if notify_before_tools
        else ""
    )
    script = """
import json
import sys

for line in sys.stdin:
    message = json.loads(line)
    if "id" not in message:
        continue
    method = message.get("method")
    if method == "initialize":
        response = {
            "jsonrpc": "2.0",
            "id": message["id"],
            "result": {"protocolVersion": "2025-06-18", "capabilities": {}},
        }
    elif method == "tools/list":
NOTIFICATION
        response = {"jsonrpc": "2.0", "id": message["id"], "result": RESULT_JSON}
    else:
        response = {
            "jsonrpc": "2.0",
            "id": message["id"],
            "error": {"code": -32601, "message": "not found"},
        }
    print(json.dumps(response), flush=True)
""".replace("RESULT_JSON", result).replace("NOTIFICATION", notification)
    path = tmp_path / "server.py"
    path.write_text(script, encoding="utf-8")
    return path


def _python_command(script: Path) -> str:
    return f'"{sys.executable}" "{script}"'
