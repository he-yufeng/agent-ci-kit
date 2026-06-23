from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from agentci.mcpgate.checker import check_stdio_server

FIXTURES = Path(__file__).parent / "fixtures"


def command_for(name: str) -> str:
    return f'"{sys.executable}" "{FIXTURES / name}"'


def test_good_server_passes() -> None:
    result = asyncio.run(check_stdio_server(command_for("good_server.py"), timeout=10))

    assert result.status == "passed"
    assert [tool.name for tool in result.tools] == ["echo"]
    assert result.findings == []


def test_empty_server_warns() -> None:
    result = asyncio.run(check_stdio_server(command_for("empty_server.py"), timeout=10))

    assert result.status == "warning"
    assert any(finding.code == "no_tools" for finding in result.findings)


def test_secret_in_tool_metadata_fails() -> None:
    result = asyncio.run(check_stdio_server(command_for("secret_server.py"), timeout=10))

    assert result.status == "failed"
    assert any(finding.code == "secret_leak" for finding in result.findings)


def test_crash_server_fails() -> None:
    result = asyncio.run(check_stdio_server(command_for("crash_server.py"), timeout=10))

    assert result.status == "failed"
    assert any(finding.code == "server_error" for finding in result.findings)


def test_timeout_server_fails() -> None:
    result = asyncio.run(check_stdio_server(command_for("timeout_server.py"), timeout=0.5))

    assert result.status == "failed"
    assert any(finding.code == "server_timeout" for finding in result.findings)
