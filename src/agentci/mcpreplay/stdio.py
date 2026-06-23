from __future__ import annotations

import json
import shlex
import subprocess
import sys
from collections.abc import Iterable
from typing import Any

from .transcript import TranscriptEvent


def default_probe_messages() -> list[dict[str, Any]]:
    return [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "mcpreplay", "version": "0.1.0"},
            },
        },
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]


def record_stdio(
    command: str,
    messages: Iterable[dict[str, Any]] | None = None,
) -> list[TranscriptEvent]:
    events: list[TranscriptEvent] = []
    seq = 1
    with _start_server(command) as proc:
        for message in messages or default_probe_messages():
            _write_message(proc, message)
            events.append(TranscriptEvent(seq=seq, direction="client", message=message))
            seq += 1

            if "id" not in message:
                continue

            response = _read_message(proc)
            events.append(TranscriptEvent(seq=seq, direction="server", message=response))
            seq += 1
    return events


class StdioServer:
    def __init__(self, command: str):
        self.command = command
        self.proc: subprocess.Popen[str] | None = None

    def __enter__(self) -> subprocess.Popen[str]:
        self.proc = subprocess.Popen(
            self.command if _uses_shell_command() else shlex.split(self.command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            shell=_uses_shell_command(),
        )
        return self.proc

    def __exit__(self, *_exc: object) -> None:
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None


def _start_server(command: str) -> StdioServer:
    return StdioServer(command)


def _write_message(proc: subprocess.Popen[str], message: dict[str, Any]) -> None:
    if proc.stdin is None:
        raise RuntimeError("server stdin is closed")
    proc.stdin.write(json.dumps(message, separators=(",", ":")))
    proc.stdin.write("\n")
    proc.stdin.flush()


def _read_message(proc: subprocess.Popen[str]) -> dict[str, Any]:
    if proc.stdout is None:
        raise RuntimeError("server stdout is closed")
    line = proc.stdout.readline()
    if not line:
        stderr = proc.stderr.read() if proc.stderr else ""
        raise RuntimeError(f"server exited before sending a response: {stderr.strip()}")
    try:
        message = json.loads(line)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"server wrote non-JSON output: {line.strip()}") from exc
    if not isinstance(message, dict):
        raise RuntimeError("server response must be a JSON object")
    return message


def _uses_shell_command() -> bool:
    return sys.platform == "win32"
