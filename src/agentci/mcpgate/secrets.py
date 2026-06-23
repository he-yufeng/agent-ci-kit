from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecretFinding:
    kind: str
    where: str


_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai_style_key", re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")),
    # GitHub's six official token prefixes: ghp (classic PAT), gho (OAuth),
    # ghu (user-to-server), ghs (server-to-server, e.g. the Actions GITHUB_TOKEN),
    # ghr (refresh), and github_pat (fine-grained PAT).
    ("github_token", re.compile(r"\b(?:gh[oprsu]|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
)


def scan_text(text: str, where: str) -> list[SecretFinding]:
    if not text:
        return []

    findings: list[SecretFinding] = []
    for kind, pattern in _PATTERNS:
        if pattern.search(text):
            findings.append(SecretFinding(kind=kind, where=where))
    return findings
