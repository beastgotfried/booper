"""Public SDK configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EnshittifyConfig:
    output_root: Path | None = None
    provider: str = "none"
    api_key: str | None = None
