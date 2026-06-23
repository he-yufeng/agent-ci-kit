from __future__ import annotations

from pathlib import Path

from .index import build_index
from .models import FileRecord, RankedFile
from .sources import collect_signals


def rank_files(
    repo: str | Path,
    *,
    issue_text: str = "",
    diff_text: str = "",
    failure_text: str = "",
    top: int = 12,
    max_file_bytes: int = 200_000,
) -> list[RankedFile]:
    signals = collect_signals(issue_text, diff_text, failure_text)
    records = build_index(repo, max_file_bytes=max_file_bytes)
    scores: dict[str, float] = {}
    reasons: dict[str, list[str]] = {}
    by_path = {record.path: record for record in records}

    for record in records:
        score, file_reasons = _score_record(record, signals.terms)
        if _path_matches(record.path, signals.mentioned_paths):
            score += 45
            file_reasons.append("mentioned directly")
        if _path_matches(record.path, signals.trace_paths):
            score += 38
            file_reasons.append("appears in stack trace")
        if _path_matches(record.path, signals.diff_paths):
            score += 28
            file_reasons.append("appears in diff")
        if score > 0:
            scores[record.path] = score
            reasons[record.path] = file_reasons

    _apply_import_boost(by_path, scores, reasons)
    _apply_test_sibling_boost(by_path, scores, reasons)

    ranked = [
        RankedFile(path=path, score=round(score, 2), reasons=_dedupe(reasons.get(path, [])))
        for path, score in scores.items()
    ]
    ranked.sort(key=lambda item: (-item.score, item.path))
    return ranked[:top]


def _score_record(record: FileRecord, terms: tuple[str, ...]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    lowered_path = record.path.lower()
    lowered_text = record.text.lower()

    path_hits = [term for term in terms if term in lowered_path]
    if path_hits:
        score += min(24, 8 * len(path_hits))
        reasons.append("path matches task terms")

    text_hits = 0
    for term in terms[:60]:
        if term in lowered_text:
            text_hits += lowered_text.count(term)
    if text_hits:
        score += min(35, 2.5 * text_hits)
        reasons.append("content matches task terms")

    return score, reasons


def _apply_import_boost(
    records: dict[str, FileRecord],
    scores: dict[str, float],
    reasons: dict[str, list[str]],
) -> None:
    initial = dict(scores)
    reverse: dict[str, set[str]] = {path: set() for path in records}
    for path, record in records.items():
        for imported in record.imports:
            reverse.setdefault(imported, set()).add(path)

    for path, score in initial.items():
        record = records.get(path)
        if not record:
            continue
        for imported in record.imports:
            if imported in records and imported not in initial:
                scores[imported] = max(scores.get(imported, 0), score * 0.28)
                reasons.setdefault(imported, []).append(f"imported by {path}")
        for importer in reverse.get(path, set()):
            if importer not in initial:
                scores[importer] = max(scores.get(importer, 0), score * 0.22)
                reasons.setdefault(importer, []).append(f"imports {path}")


def _apply_test_sibling_boost(
    records: dict[str, FileRecord],
    scores: dict[str, float],
    reasons: dict[str, list[str]],
) -> None:
    initial = dict(scores)
    for source_path, source_score in initial.items():
        if _looks_like_test(source_path):
            continue
        stem = Path(source_path).stem.lower()
        if not stem:
            continue
        for candidate in records:
            if not _looks_like_test(candidate):
                continue
            candidate_stem = Path(candidate).stem.lower()
            if stem in candidate_stem or candidate_stem in {f"test_{stem}", f"{stem}_test"}:
                scores[candidate] = max(scores.get(candidate, 0), source_score * 0.24)
                reason = f"test sibling for {source_path}"
                if reason not in reasons.setdefault(candidate, []):
                    reasons[candidate].append(reason)


def _looks_like_test(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    basename = normalized.rsplit("/", 1)[-1]
    return (
        normalized.startswith("tests/") or "/tests/" in normalized or basename.startswith("test_")
    )


def _path_matches(path: str, candidates: frozenset[str]) -> bool:
    if not candidates:
        return False
    normalized = path.lower().replace("\\", "/")
    basename = normalized.rsplit("/", 1)[-1]
    for candidate in candidates:
        lowered = candidate.lower().replace("\\", "/")
        if normalized == lowered or normalized.endswith(f"/{lowered}") or basename == lowered:
            return True
    return False


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result
