from __future__ import annotations

import json
from dataclasses import asdict

from .models import RankedFile


def to_json(files: list[RankedFile]) -> str:
    return json.dumps([asdict(file) for file in files], indent=2, ensure_ascii=False) + "\n"


def to_markdown(files: list[RankedFile], *, title: str = "PatchContext Pack") -> str:
    lines = [
        f"# {title}",
        "",
        "These are the files most likely to matter for the current task. Scores are",
        "heuristic, so use this as a starting map, not a replacement for reading code.",
        "",
    ]
    if not files:
        lines.extend(["No files matched the supplied issue, diff, or failure log.", ""])
        return "\n".join(lines)

    lines.append("| Rank | File | Score | Why selected |")
    lines.append("|---:|---|---:|---|")
    for index, file in enumerate(files, start=1):
        reason = "; ".join(file.reasons) if file.reasons else "weak contextual match"
        lines.append(f"| {index} | `{file.path}` | {file.score:.2f} | {reason} |")
    lines.append("")
    lines.append("## How to use this pack")
    lines.append("")
    lines.append("1. Read the top-ranked files first.")
    lines.append("2. Check the listed reasons before editing.")
    lines.append(
        "3. If the task still feels under-specified, add the failing log or diff and rerun."
    )
    lines.append("")
    return "\n".join(lines)
