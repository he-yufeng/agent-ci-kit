"""Thin wrapper around gh for fetching run logs."""

from __future__ import annotations

import subprocess
from pathlib import Path


def fetch_run_log(repo: str, run_id: str, out: str | Path) -> Path:
    path = Path(out)
    result = subprocess.run(
        ["gh", "run", "view", run_id, "--repo", repo, "--log"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "gh run view failed"
        raise RuntimeError(message)
    path.write_text(result.stdout, encoding="utf-8")
    return path
