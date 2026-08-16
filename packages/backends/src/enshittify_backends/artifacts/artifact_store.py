"""Artifact writing helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def archive_directory(source: Path, destination_without_suffix: Path) -> Path:
    destination_without_suffix.parent.mkdir(parents=True, exist_ok=True)
    archive = shutil.make_archive(
        str(destination_without_suffix),
        "zip",
        root_dir=source.parent,
        base_dir=source.name,
    )
    return Path(archive)
