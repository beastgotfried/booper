"""Public in-process SDK client."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from enshittify_backends import prepare_workspace
from enshittify_core import RepositoryHarness, RepositoryRunResult

from enshittify_sdk.config import EnshittifyConfig


class Enshittify:
    """Run the deterministic harness without an app server."""

    def __init__(
        self,
        *,
        output_root: str | Path | None = None,
        provider: str = "none",
        api_key: str | None = None,
    ) -> None:
        self.config = EnshittifyConfig(
            output_root=Path(output_root).expanduser() if output_root else None,
            provider=provider,
            api_key=api_key,
        )

    def run_repository(
        self,
        source: str,
        *,
        ref: str | None = None,
        profile: str = "maximum",
        intensity: str = "high",
        budget: int | None = None,
        include_tests: bool = False,
        dry_run: bool = False,
        tools: Iterable[str] | None = None,
        output: str = "workspace",
        max_file_bytes: int = 1_000_000,
    ) -> RepositoryRunResult:
        workspace = prepare_workspace(
            source,
            output_root=self.config.output_root,
            ref=ref,
        )
        return RepositoryHarness().run(
            workspace,
            profile_name=profile,
            intensity=intensity,
            budget=budget,
            include_tests=include_tests,
            dry_run=dry_run,
            tools=tools,
            output=output,
            max_file_bytes=max_file_bytes,
        )
