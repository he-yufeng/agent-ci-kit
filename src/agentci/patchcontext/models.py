from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Signals:
    terms: tuple[str, ...]
    mentioned_paths: frozenset[str]
    trace_paths: frozenset[str]
    diff_paths: frozenset[str]


@dataclass
class FileRecord:
    path: str
    text: str
    imports: set[str] = field(default_factory=set)


@dataclass
class RankedFile:
    path: str
    score: float
    reasons: list[str]
