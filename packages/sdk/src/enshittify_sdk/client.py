"""Public in-process SDK client."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from enshittify_backends import prepare_workspace
from enshittify_core import RepositoryHarness, RepositoryRunResult
from enshittify_providers import ModelProvider, create_provider

from enshittify_sdk.config import EnshittifyConfig


class Enshittify:
    """Run the deterministic or model-directed harness without an app server."""

    def __init__(
        self,
        *,
        output_root: str | Path | None = None,
        provider: str | ModelProvider = "none",
        api_key: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        provider_timeout: float = 120.0,
        provider_max_retries: int = 2,
        provider_max_tokens: int = 8192,
        mode: str = "auto",
        allow_llm_rewrites: bool = True,
        max_agent_steps: int = 24,
        max_agent_read_chars: int = 24_000,
    ) -> None:
        self.config = EnshittifyConfig(
            output_root=Path(output_root).expanduser() if output_root else None,
            provider=provider,
            api_key=api_key,
            model=model,
            temperature=temperature,
            provider_timeout=provider_timeout,
            provider_max_retries=provider_max_retries,
            provider_max_tokens=provider_max_tokens,
            mode=mode,
            allow_llm_rewrites=allow_llm_rewrites,
            max_agent_steps=max_agent_steps,
            max_agent_read_chars=max_agent_read_chars,
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
        mode: str | None = None,
        allow_llm_rewrites: bool | None = None,
        max_agent_steps: int | None = None,
        max_agent_read_chars: int | None = None,
        instruction: str | None = None,
    ) -> RepositoryRunResult:
        resolved_mode = self._resolve_mode(mode)
        model_provider = self._resolve_provider(resolved_mode)
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
            provider=model_provider,
            mode=resolved_mode,
            allow_llm_rewrites=(
                self.config.allow_llm_rewrites
                if allow_llm_rewrites is None
                else allow_llm_rewrites
            ),
            max_agent_steps=(
                self.config.max_agent_steps
                if max_agent_steps is None
                else max_agent_steps
            ),
            max_agent_read_chars=(
                self.config.max_agent_read_chars
                if max_agent_read_chars is None
                else max_agent_read_chars
            ),
            instruction=instruction,
        )

    def _resolve_mode(self, override: str | None) -> str:
        mode = override or self.config.mode
        if mode not in {"agent", "auto", "deterministic", "hybrid"}:
            raise ValueError(
                f"Unknown harness mode `{mode}`. Choose from: agent, auto, deterministic, hybrid."
            )
        if mode != "auto":
            return mode
        provider = self.config.provider
        if isinstance(provider, str) and provider.strip().lower() in {
            "none",
            "off",
            "disabled",
        }:
            return "deterministic"
        return "hybrid"

    def _resolve_provider(self, mode: str) -> ModelProvider | None:
        if mode == "deterministic":
            return None
        provider = create_provider(
            self.config.provider,
            api_key=self.config.api_key,
            model=self.config.model,
            temperature=self.config.temperature,
            timeout=self.config.provider_timeout,
            max_retries=self.config.provider_max_retries,
            max_tokens=self.config.provider_max_tokens,
        )
        if provider is None:
            raise ValueError(f"Harness mode `{mode}` requires an LLM provider.")
        return provider
