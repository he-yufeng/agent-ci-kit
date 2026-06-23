from __future__ import annotations

import json
from typing import Any

from .transcript import TranscriptEvent, summarize_transcript


def render_json(events: list[TranscriptEvent]) -> str:
    return json.dumps(summarize_transcript(events), ensure_ascii=False, indent=2)


def render_markdown(events: list[TranscriptEvent]) -> str:
    summary = summarize_transcript(events)
    lines = [
        "# MCPReplay Report",
        "",
        f"- Events: {summary['events']}",
        f"- Client events: {summary['client_events']}",
        f"- Server events: {summary['server_events']}",
        f"- Requests: {summary['requests']}",
        f"- Responses: {summary['responses']}",
        f"- Notifications: {summary['notifications']}",
        "",
        "## Methods",
        "",
    ]
    methods: dict[str, int] = summary["methods"]
    if methods:
        for method, count in sorted(methods.items()):
            lines.append(f"- `{method}`: {count}")
    else:
        lines.append("- No methods recorded.")

    lines.extend(["", "## Warnings", ""])
    warnings: list[str] = summary["warnings"]
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None.")

    lines.extend(["", "## Event Timeline", ""])
    for event in events:
        message = event.message
        label = _event_label(message)
        lines.append(f"- `{event.seq}` {event.direction}: {label}")

    return "\n".join(lines) + "\n"


def _event_label(message: dict[str, Any]) -> str:
    if "method" in message:
        method = message.get("method")
        if "id" in message:
            return f"request `{method}` id={message['id']!r}"
        return f"notification `{method}`"
    if "id" in message:
        kind = "error" if "error" in message else "result"
        return f"response {kind} id={message['id']!r}"
    return "message"
