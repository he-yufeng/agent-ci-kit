from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HIGH_RISK_LEVELS = {"write", "network", "dangerous", "admin"}


@dataclass(frozen=True)
class ToolSpec:
    name: str
    risk: str = "read"
    requires_confirmation: bool = False

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> ToolSpec:
        return cls(
            name=str(raw["name"]),
            risk=str(raw.get("risk", "read")).lower(),
            requires_confirmation=bool(raw.get("requires_confirmation", False)),
        )

    @property
    def is_high_risk(self) -> bool:
        return self.risk in HIGH_RISK_LEVELS or self.requires_confirmation


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: Any = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> ToolCall:
        if "function" in raw:
            function = raw["function"] or {}
            return cls(name=str(function.get("name", "")), arguments=function.get("arguments", {}))

        return cls(
            name=str(raw.get("name") or raw.get("tool") or raw.get("function_name") or ""),
            arguments=raw.get("arguments", raw.get("args", {})),
        )


@dataclass(frozen=True)
class TranscriptEvent:
    role: str
    content: str = ""
    name: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    untrusted: bool = False
    confirms: list[str] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> TranscriptEvent:
        confirms_raw = raw.get("confirms", raw.get("confirmation_for", []))
        if isinstance(confirms_raw, str):
            confirms = [confirms_raw]
        else:
            confirms = [str(item) for item in confirms_raw]

        calls = raw.get("tool_calls", raw.get("calls", []))
        return cls(
            role=str(raw.get("role", "")),
            content=str(raw.get("content", "")),
            name=raw.get("name"),
            tool_calls=[ToolCall.from_raw(item) for item in calls],
            untrusted=bool(raw.get("untrusted", raw.get("trusted") is False)),
            confirms=confirms,
        )


@dataclass(frozen=True)
class Expectation:
    denied: set[str] = field(default_factory=set)
    allowed: set[str] = field(default_factory=set)
    must_call: set[str] = field(default_factory=set)

    @classmethod
    def from_raw(cls, raw: dict[str, Any] | None) -> Expectation:
        raw = raw or {}
        return cls(
            denied={str(item) for item in raw.get("denied", [])},
            allowed={str(item) for item in raw.get("allowed", [])},
            must_call={str(item) for item in raw.get("must_call", raw.get("must_call_tools", []))},
        )


@dataclass(frozen=True)
class Fixture:
    path: Path
    name: str
    tools: dict[str, ToolSpec]
    transcript: list[TranscriptEvent]
    expect: Expectation


@dataclass(frozen=True)
class Finding:
    fixture: str
    tool: str
    rule: str
    message: str
    event_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture": self.fixture,
            "tool": self.tool,
            "rule": self.rule,
            "message": self.message,
            "event_index": self.event_index,
        }


@dataclass(frozen=True)
class RunResult:
    fixture: str
    path: str
    passed: bool
    called_tools: list[str]
    findings: list[Finding]

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture": self.fixture,
            "path": self.path,
            "passed": self.passed,
            "called_tools": self.called_tools,
            "findings": [finding.to_dict() for finding in self.findings],
        }
