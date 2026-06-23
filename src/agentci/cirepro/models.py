"""Small data objects used by ActionRepro."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class LogLine:
    source: Path
    number: int
    job: str
    step: str
    timestamp: str
    text: str


@dataclass(slots=True)
class Failure:
    category: str
    job: str
    step: str
    source: Path
    line: int
    headline: str
    evidence: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    advice: str = ""


@dataclass(slots=True)
class Analysis:
    paths: list[Path]
    failures: list[Failure]
    command_count: int
    line_count: int
