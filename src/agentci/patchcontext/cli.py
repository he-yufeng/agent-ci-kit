from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from .pack import to_json, to_markdown
from .ranker import rank_files
from .sources import read_optional_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="patchcontext",
        description="Generate issue-specific context packs for coding agents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_scan(subparsers)
    _add_from_failure(subparsers)
    _add_from_diff(subparsers)

    args = parser.parse_args(argv)
    if args.command == "scan":
        return _run_scan(args)
    if args.command == "from-failure":
        return _run_failure(args)
    if args.command == "from-diff":
        return _run_diff(args)
    parser.error(f"unknown command: {args.command}")
    return 2


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".", help="Repository root. Defaults to current dir.")
    parser.add_argument("--top", type=int, default=12, help="Number of files to include.")
    parser.add_argument(
        "--max-file-bytes",
        type=int,
        default=200_000,
        help="Skip files larger than this many bytes while indexing.",
    )
    parser.add_argument("--format", choices=["md", "json"], default="md", help="Output format.")
    parser.add_argument("--output", "-o", help="Write output to this file instead of stdout.")


def _add_scan(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("scan", help="Build a context pack from issue/diff/log inputs.")
    _add_common(parser)
    parser.add_argument("--issue", help="Issue, bug report, or task markdown file.")
    parser.add_argument("--diff", help="Existing diff text file.")
    parser.add_argument("--failure", help="Failure log or traceback file.")


def _add_from_failure(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("from-failure", help="Build a pack from a failure log.")
    _add_common(parser)
    parser.add_argument("log", help="Failure log file.")


def _add_from_diff(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("from-diff", help="Build a pack from git diff against a base.")
    _add_common(parser)
    parser.add_argument("--base", default="main", help="Base ref. Defaults to main.")


def _run_scan(args: argparse.Namespace) -> int:
    return _emit(
        repo=args.repo,
        issue_text=read_optional_text(args.issue),
        diff_text=read_optional_text(args.diff),
        failure_text=read_optional_text(args.failure),
        top=args.top,
        max_file_bytes=args.max_file_bytes,
        fmt=args.format,
        output=args.output,
    )


def _run_failure(args: argparse.Namespace) -> int:
    return _emit(
        repo=args.repo,
        failure_text=Path(args.log).read_text(encoding="utf-8"),
        top=args.top,
        max_file_bytes=args.max_file_bytes,
        fmt=args.format,
        output=args.output,
    )


def _run_diff(args: argparse.Namespace) -> int:
    repo = Path(args.repo)
    diff = _git_diff(repo, args.base)
    return _emit(
        repo=repo,
        diff_text=diff,
        top=args.top,
        max_file_bytes=args.max_file_bytes,
        fmt=args.format,
        output=args.output,
    )


def _emit(
    *,
    repo: str | Path,
    issue_text: str = "",
    diff_text: str = "",
    failure_text: str = "",
    top: int,
    max_file_bytes: int,
    fmt: str,
    output: str | None,
) -> int:
    if max_file_bytes <= 0:
        raise SystemExit("--max-file-bytes must be greater than zero")
    files = rank_files(
        repo,
        issue_text=issue_text,
        diff_text=diff_text,
        failure_text=failure_text,
        top=top,
        max_file_bytes=max_file_bytes,
    )
    rendered = to_json(files) if fmt == "json" else to_markdown(files)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


def _git_diff(repo: Path, base: str) -> str:
    candidates = [
        ["git", "-C", str(repo), "diff", "--unified=0", f"{base}...HEAD"],
        ["git", "-C", str(repo), "diff", "--unified=0", base],
    ]
    for command in candidates:
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode == 0:
            return result.stdout
    raise SystemExit(f"git diff failed against {base!r}")


if __name__ == "__main__":
    raise SystemExit(main())
