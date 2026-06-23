from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .models import RunResult


def summarize_findings(results: list[RunResult]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for result in results:
        counts.update(finding.rule for finding in result.findings)
    return dict(sorted(counts.items()))


def results_to_json(results: list[RunResult]) -> str:
    payload = {
        "passed": all(result.passed for result in results),
        "total": len(results),
        "failed": sum(not result.passed for result in results),
        "finding_summary": summarize_findings(results),
        "results": [result.to_dict() for result in results],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def load_results(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def results_to_markdown(payload: dict[str, Any]) -> str:
    status = "passed" if payload.get("passed") else "failed"
    lines = [
        "# Agent ToolFence Report",
        "",
        f"- Status: **{status}**",
        f"- Fixtures: {payload.get('total', 0)}",
        f"- Failed: {payload.get('failed', 0)}",
        "",
    ]

    summary = payload.get("finding_summary") or {}
    if summary:
        lines.extend(["## Finding Summary", "", "| Rule | Count |", "|---|---:|"])
        for rule, count in sorted(summary.items(), key=lambda item: (-int(item[1]), item[0])):
            lines.append(f"| `{rule}` | {count} |")
        lines.append("")

    for item in payload.get("results", []):
        mark = "PASS" if item.get("passed") else "FAIL"
        lines.append(f"## {mark}: {item.get('fixture')}")
        lines.append("")
        lines.append(f"- Path: `{item.get('path')}`")
        called = ", ".join(f"`{name}`" for name in item.get("called_tools", [])) or "_none_"
        lines.append(f"- Called tools: {called}")

        findings = item.get("findings", [])
        if findings:
            lines.append("")
            lines.append("| Rule | Tool | Event | Message |")
            lines.append("|---|---|---:|---|")
            for finding in findings:
                event = finding.get("event_index")
                lines.append(
                    "| {rule} | `{tool}` | {event} | {message} |".format(
                        rule=finding.get("rule", ""),
                        tool=finding.get("tool", ""),
                        event="" if event is None else event,
                        message=str(finding.get("message", "")).replace("|", "\\|"),
                    )
                )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
