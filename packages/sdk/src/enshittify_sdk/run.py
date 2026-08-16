"""One-call SDK convenience function."""

from __future__ import annotations

from pathlib import Path

from enshittify_core import RepositoryRunResult
from enshittify_providers import ModelProvider

from enshittify_sdk.client import Enshittify


def run_repository(
    source: str,
    *,
    output_root: str | Path | None = None,
    profile: str = "maximum",
    intensity: str = "high",
    provider: str | ModelProvider = "none",
    api_key: str | None = None,
    model: str | None = None,
    mode: str = "auto",
) -> RepositoryRunResult:
    return Enshittify(
        output_root=output_root,
        provider=provider,
        api_key=api_key,
        model=model,
        mode=mode,
    ).run_repository(
        source,
        profile=profile,
        intensity=intensity,
    )
