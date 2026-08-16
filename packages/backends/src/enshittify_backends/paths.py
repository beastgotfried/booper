"""Source classification and path helpers."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

_SCP_GIT_URL = re.compile(r"^[^/@\s]+@[^/:\s]+:[^\s]+$")


def classify_source(source: str) -> str:
    """Classify a source as a local directory, GitHub repository, or Git URL."""
    local_path = Path(source).expanduser()
    if local_path.exists():
        if not local_path.is_dir():
            raise ValueError(f"Local source is not a directory: {local_path}")
        return "local"

    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        if parsed.username or parsed.password:
            raise ValueError(
                "Credentials in repository URLs are not accepted; use a Git credential helper."
            )
        if parsed.hostname and parsed.hostname.lower() == "github.com":
            return "github"
        return "git"

    if parsed.scheme in {"ssh", "git", "file"} or _SCP_GIT_URL.match(source):
        return "github" if "github.com" in source.lower() else "git"

    raise ValueError(f"Source does not exist and is not a supported Git URL: {source}")


def default_output_root(current_directory: Path | None = None) -> Path:
    base = (current_directory or Path.cwd()).resolve()
    return base / ".enshittify" / "runs"
