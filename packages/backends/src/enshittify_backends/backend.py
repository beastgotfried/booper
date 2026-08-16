"""Isolated local and Git repository workspace preparation."""

from __future__ import annotations

import secrets
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from enshittify_backends.paths import classify_source, default_output_root

EXCLUDED_NAMES = frozenset(
    {
        ".enshittify",
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


class WorkspaceError(RuntimeError):
    """Raised when a repository cannot be staged safely."""


@dataclass(frozen=True)
class PreparedWorkspace:
    run_id: str
    source: str
    source_kind: str
    revision: str | None
    run_dir: Path
    original_dir: Path
    working_dir: Path
    artifacts_dir: Path

    def to_dict(self) -> dict[str, str | None]:
        payload = asdict(self)
        return {
            key: str(value) if isinstance(value, Path) else value
            for key, value in payload.items()
        }


def _new_run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"run-{timestamp}-{secrets.token_hex(3)}"


def _run_git(arguments: list[str], *, cwd: Path | None = None) -> str:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except FileNotFoundError as error:
        raise WorkspaceError("Git is required for repository URL inputs.") from error
    except subprocess.TimeoutExpired as error:
        raise WorkspaceError("Git operation timed out after 180 seconds.") from error
    except subprocess.CalledProcessError as error:
        details = (error.stderr or error.stdout or "Git command failed.").strip()
        raise WorkspaceError(details) from error
    return completed.stdout.strip()


def _copy_ignore(output_root: Path) -> Callable[[str, list[str]], set[str]]:
    resolved_output = output_root.resolve()

    def ignore(directory: str, names: list[str]) -> set[str]:
        parent = Path(directory)
        ignored: set[str] = set()
        for name in names:
            candidate = parent / name
            if name in EXCLUDED_NAMES or candidate.is_symlink():
                ignored.add(name)
                continue
            resolved_candidate = candidate.resolve()
            if resolved_candidate == resolved_output or resolved_output.is_relative_to(
                resolved_candidate
            ):
                ignored.add(name)
        return ignored

    return ignore


def _copy_local_repository(source: Path, destination: Path, output_root: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=_copy_ignore(output_root),
        copy_function=shutil.copy2,
    )


def _clone_repository(source: str, destination: Path, ref: str | None) -> str | None:
    _run_git(["clone", "--quiet", "--depth", "1", "--", source, str(destination)])
    if ref:
        _run_git(["fetch", "--quiet", "--depth", "1", "origin", ref], cwd=destination)
        _run_git(["checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=destination)
    revision = _run_git(["rev-parse", "HEAD"], cwd=destination)
    return revision or None


def _local_revision(source: Path) -> str | None:
    try:
        revision = _run_git(["rev-parse", "HEAD"], cwd=source)
    except WorkspaceError:
        return None
    return revision or None


def prepare_workspace(
    source: str,
    *,
    output_root: str | Path | None = None,
    ref: str | None = None,
    run_id: str | None = None,
) -> PreparedWorkspace:
    """Copy or clone a repository into an isolated, persistent run directory."""
    source_kind = classify_source(source)
    resolved_output = Path(output_root or default_output_root()).expanduser().resolve()
    local_source = (
        Path(source).expanduser().resolve() if source_kind == "local" else None
    )
    if local_source is not None and resolved_output == local_source:
        raise WorkspaceError(
            "The output directory cannot be the source directory itself."
        )
    resolved_output.mkdir(parents=True, exist_ok=True)

    active_run_id = run_id or _new_run_id()
    run_dir = resolved_output / active_run_id
    original_dir = run_dir / "original"
    working_dir = run_dir / "workspace"
    artifacts_dir = run_dir / "artifacts"

    try:
        run_dir.mkdir(parents=False, exist_ok=False)
    except FileExistsError as error:
        raise WorkspaceError(f"Run directory already exists: {run_dir}") from error

    try:
        if source_kind == "local":
            assert local_source is not None
            _copy_local_repository(local_source, original_dir, resolved_output)
            revision = _local_revision(local_source)
            display_source = str(local_source)
        else:
            revision = _clone_repository(source, original_dir, ref)
            display_source = source

        shutil.copytree(
            original_dir,
            working_dir,
            ignore=_copy_ignore(resolved_output),
            copy_function=shutil.copy2,
        )
        artifacts_dir.mkdir()
    except Exception:
        shutil.rmtree(run_dir, ignore_errors=True)
        raise

    return PreparedWorkspace(
        run_id=active_run_id,
        source=display_source,
        source_kind=source_kind,
        revision=revision,
        run_dir=run_dir,
        original_dir=original_dir,
        working_dir=working_dir,
        artifacts_dir=artifacts_dir,
    )
