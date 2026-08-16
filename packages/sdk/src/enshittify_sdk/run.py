"""One-call SDK convenience function."""

from __future__ import annotations

from pathlib import Path

from enshittify_core import RepositoryRunResult
from enshittify_providers import CodxProvider, ModelProvider

from enshittify_sdk.client import Enshittify


def run_repository(
    source: str,
    *,
    output_root: str | Path | None = None,
    profile: str = "maximum",
    intensity: str = "high",
    provider: str | ModelProvider | CodxProvider = "none",
    api_key: str | None = None,
    model: str | None = None,
    mode: str = "auto",
    codx_command: str | None = None,
    codx_timeout: float = 1_800.0,
    codx_yolo: bool = True,
) -> RepositoryRunResult:
    return Enshittify(
        output_root=output_root,
        provider=provider,
        api_key=api_key,
        model=model,
        mode=mode,
        codx_command=codx_command,
        codx_timeout=codx_timeout,
        codx_yolo=codx_yolo,
    ).run_repository(
        source,
        profile=profile,
        intensity=intensity,
    )
