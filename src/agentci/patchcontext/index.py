from __future__ import annotations

import ast
import re
from pathlib import Path

from .models import FileRecord

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
}
TEXT_SUFFIXES = {
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".md",
    ".rst",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
}
IMPORT_RE = re.compile(r"""(?:from|import)\s+["'](\.{1,2}/[^"']+)["']""")


def build_index(repo: str | Path, max_file_bytes: int = 200_000) -> list[FileRecord]:
    root = Path(repo).resolve()
    records: list[FileRecord] = []
    for path in _iter_text_files(root, max_file_bytes):
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(root).as_posix()
        records.append(FileRecord(path=rel, text=text, imports=_extract_imports(root, path, text)))
    return records


def _iter_text_files(root: Path, max_file_bytes: int):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.relative_to(root).parts)
        if parts & EXCLUDED_DIRS:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.stat().st_size > max_file_bytes:
            continue
        yield path


def _extract_imports(root: Path, path: Path, text: str) -> set[str]:
    if path.suffix == ".py":
        return _extract_python_imports(root, path, text)
    if path.suffix in {".js", ".jsx", ".ts", ".tsx"}:
        return _extract_js_imports(root, path, text)
    return set()


def _extract_python_imports(root: Path, path: Path, text: str) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()

    # The importing file's package directory, relative to root, so relative
    # imports (from .x / from ..x / from . import x) resolve to siblings.
    pkg_dir = path.relative_to(root).parent

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.update(_module_to_paths(root, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                # absolute import
                if node.module:
                    imported.update(_module_to_paths(root, node.module))
                continue
            # relative import: walk up (level - 1) packages from the importer
            base = pkg_dir
            for _ in range(node.level - 1):
                base = base.parent
            if node.module:
                rel = (base / node.module.replace(".", "/")).as_posix()
                imported.update(_paths_for_rel(root, rel))
            else:
                # `from . import a, b` -> a and b are submodules of `base`
                for alias in node.names:
                    rel = (base / alias.name.replace(".", "/")).as_posix()
                    imported.update(_paths_for_rel(root, rel))
    return imported


def _paths_for_rel(root: Path, rel: str) -> set[str]:
    candidates = {f"{rel}.py", f"{rel}/__init__.py"}
    return {path for path in candidates if (root / path).exists()}


def _module_to_paths(root: Path, module: str) -> set[str]:
    return _paths_for_rel(root, module.replace(".", "/"))


def _extract_js_imports(root: Path, path: Path, text: str) -> set[str]:
    found: set[str] = set()
    for match in IMPORT_RE.finditer(text):
        target = match.group(1)
        resolved = (path.parent / target).resolve()
        for suffix in ("", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"):
            candidate = Path(f"{resolved}{suffix}")
            if candidate.exists() and root in candidate.parents:
                found.add(candidate.relative_to(root).as_posix())
                break
    return found
