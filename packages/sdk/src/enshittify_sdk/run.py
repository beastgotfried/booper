"""One-call SDK convenience function."""

from __future__ import annotations

from pathlib import Path

from enshittify_core import RepositoryRunResult

from enshittify_sdk.client import Enshittify


def run_repository(
    source: str,
    *,
    output_root: str | Path | None = None,
    profile: str = "maximum",
    intensity: str = "high",
) -> RepositoryRunResult:
    return Enshittify(output_root=output_root).run_repository(
        source,
        profile=profile,
        intensity=intensity,
    )
