from __future__ import annotations

import json
from pathlib import Path

from .checker import CheckResult


def write_json_report(result: CheckResult, path: Path) -> None:
    payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")


def write_markdown_report(result: CheckResult, path: Path) -> None:
    lines = [
        "# MCPReady Report",
        "",
        f"- Status: `{result.status}`",
        f"- Command: `{result.command}`",
        f"- Duration: `{result.duration_ms}ms`",
        f"- Tools: `{len(result.tools)}`",
        "",
        "## Tools",
        "",
    ]

    if result.tools:
        lines.extend(["| Name | Description | Input schema |", "|---|---|---|"])
        for tool in result.tools:
            description = (tool.description or "").replace("|", "\\|")
            lines.append(f"| `{tool.name}` | {description} | {tool.has_input_schema} |")
    else:
        lines.append("No tools returned.")

    lines.extend(["", "## Findings", ""])
    if result.findings:
        lines.extend(["| Severity | Code | Target | Message |", "|---|---|---|---|"])
        for finding in result.findings:
            target = finding.target or ""
            message = finding.message.replace("|", "\\|")
            lines.append(f"| `{finding.severity}` | `{finding.code}` | `{target}` | {message} |")
    else:
        lines.append("No findings.")

    if result.stderr_tail:
        lines.extend(["", "## Stderr Tail", "", "```text", result.stderr_tail, "```"])

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
