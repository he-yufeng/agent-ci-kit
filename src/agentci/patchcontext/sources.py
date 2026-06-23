from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .models import Signals

PATH_RE = re.compile(
    r"(?<![\w.-])([A-Za-z0-9_./\\-]+\."
    r"(?:py|pyi|js|jsx|ts|tsx|md|rst|json|yaml|yml|toml|go|rs|java|kt|c|cc|cpp|h|hpp|cs))"
)
PY_TRACE_RE = re.compile(r'File "([^"]+)", line \d+')
JS_TRACE_RE = re.compile(r"\bat .+?\(([^():]+):\d+:\d+\)")
DIFF_RE = re.compile(r"^(?:diff --git a/(\S+) b/(\S+)|\+\+\+ b/(\S+)|--- a/(\S+))$", re.MULTILINE)
WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "when",
    "where",
    "into",
    "should",
    "would",
    "could",
    "because",
    "error",
    "failed",
    "failure",
    "test",
    "tests",
    "python",
}


def read_optional_text(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8")


def collect_signals(*texts: str) -> Signals:
    combined = "\n".join(text for text in texts if text)
    mentioned = {_normalize_path(match.group(1)) for match in PATH_RE.finditer(combined)}
    traces = {_normalize_path(match.group(1)) for match in PY_TRACE_RE.finditer(combined)}
    traces.update(_normalize_path(match.group(1)) for match in JS_TRACE_RE.finditer(combined))

    diff_paths: set[str] = set()
    for match in DIFF_RE.finditer(combined):
        for group in match.groups():
            if group and group != "/dev/null":
                diff_paths.add(_normalize_path(group))

    terms = _extract_terms(combined)
    return Signals(
        terms=tuple(terms),
        mentioned_paths=frozenset(mentioned),
        trace_paths=frozenset(traces),
        diff_paths=frozenset(diff_paths),
    )


def _extract_terms(text: str, limit: int = 80) -> list[str]:
    counts: Counter[str] = Counter()
    for word in WORD_RE.findall(text):
        lowered = word.lower()
        if lowered in STOP_WORDS or len(lowered) < 3:
            continue
        counts[lowered] += 1
        for piece in _split_identifier(word):
            if piece not in STOP_WORDS and len(piece) >= 3:
                counts[piece] += 1
    return [term for term, _ in counts.most_common(limit)]


def _split_identifier(value: str) -> list[str]:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return [part.lower() for part in re.split(r"[^A-Za-z0-9]+", value) if part]


def _normalize_path(path: str) -> str:
    path = path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    for prefix in ("a/", "b/"):
        if path.startswith(prefix):
            path = path[len(prefix) :]
    return path
