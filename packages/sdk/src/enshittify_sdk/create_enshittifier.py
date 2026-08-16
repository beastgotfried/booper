"""SDK factory helper."""

from __future__ import annotations

from pathlib import Path

from enshittify_providers import ModelProvider

from enshittify_sdk.client import Enshittify


def create_enshittifier(
    *,
    output_root: str | Path | None = None,
    provider: str | ModelProvider = "none",
    api_key: str | None = None,
    model: str | None = None,
    mode: str = "auto",
) -> Enshittify:
    return Enshittify(
        output_root=output_root,
        provider=provider,
        api_key=api_key,
        model=model,
        mode=mode,
    )
