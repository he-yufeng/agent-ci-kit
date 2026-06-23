"""Parse GitHub Actions logs saved by gh or downloaded as plain text."""

from __future__ import annotations

import re
from pathlib import Path

from .models import LogLine

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T")


def clean_text(text: str) -> str:
    text = ANSI_RE.sub("", text)
    text = text.replace("\ufeff", "")
    return text.rstrip()


def parse_line(source: Path, number: int, raw: str) -> LogLine:
    text = clean_text(raw)
    parts = text.split("\t", 3)
    if len(parts) == 4 and TIMESTAMP_RE.match(parts[2]):
        return LogLine(
            source=source,
            number=number,
            job=parts[0].strip() or "-",
            step=parts[1].strip() or "-",
            timestamp=parts[2].strip(),
            text=parts[3].strip(),
        )
    return LogLine(source=source, number=number, job="-", step="-", timestamp="", text=text)


def load_lines(paths: list[Path]) -> list[LogLine]:
    lines: list[LogLine] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        for index, raw in enumerate(text.splitlines(), start=1):
            lines.append(parse_line(path, index, raw))
    return lines
