"""Repository language inspection and Python file selection."""

from __future__ import annotations

import os
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "target",
        "venv",
    }
)

LANGUAGE_EXTENSIONS = {
    ".c": "C",
    ".cpp": "C++",
    ".go": "Go",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".py": "Python",
    ".rs": "Rust",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
}


@dataclass(frozen=True)
class RepositoryInspection:
    root: str
    total_files: int
    total_bytes: int
    languages: dict[str, int]
    python_files: list[str]
    skipped_large_python_files: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _walk_files(root: Path):
    for current, directories, files in os.walk(root, followlinks=False):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in EXCLUDED_DIRECTORIES
            and not (Path(current) / directory).is_symlink()
        )
        for filename in sorted(files):
            path = Path(current) / filename
            if not path.is_symlink():
                yield path


def _is_test_file(relative_path: Path) -> bool:
    lowered_parts = {part.lower() for part in relative_path.parts}
    name = relative_path.name.lower()
    return (
        "test" in lowered_parts
        or "tests" in lowered_parts
        or name.startswith("test_")
        or name.endswith("_test.py")
    )


def iter_python_files(
    root: Path,
    *,
    include_tests: bool = False,
    max_file_bytes: int = 1_000_000,
) -> list[Path]:
    selected: list[Path] = []
    for path in _walk_files(root):
        size = path.stat().st_size
        if path.suffix.lower() != ".py" or size == 0 or size > max_file_bytes:
            continue
        relative_path = path.relative_to(root)
        if not include_tests and _is_test_file(relative_path):
            continue
        selected.append(path)
    return selected


def inspect_repository(
    root: Path,
    *,
    max_file_bytes: int = 1_000_000,
) -> RepositoryInspection:
    resolved_root = root.resolve()
    total_files = 0
    total_bytes = 0
    languages: Counter[str] = Counter()
    python_files: list[str] = []
    skipped_large_python_files: list[str] = []

    for path in _walk_files(resolved_root):
        relative = path.relative_to(resolved_root).as_posix()
        size = path.stat().st_size
        total_files += 1
        total_bytes += size
        language = LANGUAGE_EXTENSIONS.get(path.suffix.lower())
        if language:
            languages[language] += 1
        if path.suffix.lower() == ".py":
            if size <= max_file_bytes:
                python_files.append(relative)
            else:
                skipped_large_python_files.append(relative)

    return RepositoryInspection(
        root=str(resolved_root),
        total_files=total_files,
        total_bytes=total_bytes,
        languages=dict(sorted(languages.items())),
        python_files=python_files,
        skipped_large_python_files=skipped_large_python_files,
    )
