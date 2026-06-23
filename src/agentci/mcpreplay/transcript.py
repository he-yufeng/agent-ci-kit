from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Direction = Literal["client", "server"]

SECRET_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "bearer",
    "cookie",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
}

TOKEN_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{16,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
]


@dataclass(frozen=True)
class TranscriptEvent:
    seq: int
    direction: Direction
    message: dict[str, Any]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> TranscriptEvent:
        direction = data.get("direction")
        if direction not in {"client", "server"}:
            raise ValueError(f"invalid transcript direction: {direction!r}")
        message = data.get("message")
        if not isinstance(message, dict):
            raise ValueError("transcript event message must be an object")
        return cls(seq=int(data["seq"]), direction=direction, message=message)

    def to_json(self) -> dict[str, Any]:
        return {"seq": self.seq, "direction": self.direction, "message": self.message}


def load_transcript(path: str | Path) -> list[TranscriptEvent]:
    events: list[TranscriptEvent] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL event") from exc
            events.append(TranscriptEvent.from_json(data))
    _validate_sequence(events)
    return events


def save_transcript(events: list[TranscriptEvent], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for event in events:
            handle.write(json.dumps(event.to_json(), ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def redact_transcript(events: list[TranscriptEvent]) -> list[TranscriptEvent]:
    return [
        TranscriptEvent(
            seq=event.seq,
            direction=event.direction,
            message=_redact_value(event.message, parent_key=""),
        )
        for event in events
    ]


def summarize_transcript(events: list[TranscriptEvent]) -> dict[str, Any]:
    requests = 0
    responses = 0
    notifications = 0
    methods: dict[str, int] = {}
    ids: set[Any] = set()
    warnings: list[str] = []

    for event in events:
        message = event.message
        method = message.get("method")
        if isinstance(method, str):
            methods[method] = methods.get(method, 0) + 1
            if "id" in message:
                requests += 1
            else:
                notifications += 1
        elif "id" in message:
            responses += 1

        if "id" in message:
            if message["id"] in ids and event.direction == "client":
                warnings.append(f"duplicate client id: {message['id']!r}")
            ids.add(message["id"])

        if message.get("jsonrpc") != "2.0":
            warnings.append(f"event {event.seq} is missing jsonrpc=2.0")

    return {
        "events": len(events),
        "client_events": sum(1 for event in events if event.direction == "client"),
        "server_events": sum(1 for event in events if event.direction == "server"),
        "requests": requests,
        "responses": responses,
        "notifications": notifications,
        "methods": methods,
        "warnings": warnings,
    }


def _validate_sequence(events: list[TranscriptEvent]) -> None:
    expected = 1
    for event in events:
        if event.seq != expected:
            raise ValueError(f"transcript sequence expected {expected}, got {event.seq}")
        expected += 1


def _redact_value(value: Any, parent_key: str) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, child in value.items():
            if _is_secret_key(key):
                redacted[key] = "<REDACTED>"
            else:
                redacted[key] = _redact_value(child, parent_key=key)
        return redacted
    if isinstance(value, list):
        return [_redact_value(item, parent_key=parent_key) for item in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _is_secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized in SECRET_KEYS:
        return True
    if any(part in SECRET_KEYS for part in normalized.split("_")):
        return True
    # "api_key" / "apikey" is a compound that survives any prefix once the
    # separators are collapsed (x_api_key -> xapikey, openai_api_key ->
    # openaiapikey), unlike "token" it has no standalone secret word to fall
    # back on. Catch those header/env spellings without over-redacting.
    return "apikey" in normalized.replace("_", "")


def _redact_string(value: str) -> str:
    redacted = value
    for pattern in TOKEN_PATTERNS:
        redacted = pattern.sub("<REDACTED>", redacted)
    return redacted
