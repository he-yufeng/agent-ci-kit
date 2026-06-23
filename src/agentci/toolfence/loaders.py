from __future__ import annotations

import glob
import json
from pathlib import Path
from typing import Any

import yaml

from .models import Expectation, Fixture, ToolSpec, TranscriptEvent


def discover_files(paths: tuple[str, ...]) -> list[Path]:
    if not paths:
        paths = ("tests/toolfence/*.yaml", "tests/toolfence/*.yml", "tests/toolfence/*.json")

    files: list[Path] = []
    for item in paths:
        # Check for a directory first: glob.glob() returns a directory path
        # unchanged (it has no wildcard), which would otherwise add the directory
        # itself instead of expanding to the fixtures inside it.
        path = Path(item)
        if path.is_dir():
            files.extend(sorted(path.glob("*.yaml")))
            files.extend(sorted(path.glob("*.yml")))
            files.extend(sorted(path.glob("*.json")))
            continue

        matches = [Path(match) for match in glob.glob(item)]
        if matches:
            files.extend(matches)
        else:
            files.append(path)

    seen: set[Path] = set()
    unique: list[Path] = []
    for path in files:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def load_fixture(path: str | Path) -> Fixture:
    fixture_path = Path(path)
    data = _load_mapping(fixture_path)

    tools = {
        spec.name: spec for spec in (ToolSpec.from_raw(item) for item in data.get("tools", []))
    }
    transcript = [TranscriptEvent.from_raw(item) for item in data.get("transcript", [])]

    return Fixture(
        path=fixture_path,
        name=str(data.get("name") or fixture_path.stem),
        tools=tools,
        transcript=transcript,
        expect=Expectation.from_raw(data.get("expect")),
    )


def _load_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)

    text = path.read_text(encoding="utf-8")
    data = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping at the top level")
    return data
