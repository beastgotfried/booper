"""Registry and factory for model providers."""

from __future__ import annotations

from dataclasses import dataclass

from enshittify_providers.adapters.groq import (
    DEFAULT_GROQ_MODEL,
    GROQ_API_KEY_ENV,
    create_groq_provider,
)
from enshittify_providers.base import ModelProvider
from enshittify_providers.normalize import normalize_provider_name


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    description: str
    default_model: str | None
    api_key_env: str | None


PROVIDER_SPECS = (
    ProviderSpec(
        name="none",
        description="Run only the deterministic LangGraph mutation pipeline.",
        default_model=None,
        api_key_env=None,
    ),
    ProviderSpec(
        name="groq",
        description="Run the model-directed harness through GroqCloud.",
        default_model=DEFAULT_GROQ_MODEL,
        api_key_env=GROQ_API_KEY_ENV,
    ),
)


def list_provider_specs() -> list[ProviderSpec]:
    return list(PROVIDER_SPECS)


def create_provider(
    provider: str | ModelProvider,
    *,
    api_key: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    timeout: float = 120.0,
    max_retries: int = 2,
    max_tokens: int = 8192,
) -> ModelProvider | None:
    """Resolve a built-in provider name or accept an already wrapped provider."""
    if not isinstance(provider, str):
        return provider

    name = normalize_provider_name(provider)
    if name == "none":
        return None
    if name == "groq":
        return create_groq_provider(
            api_key=api_key,
            model=model,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries,
            max_tokens=max_tokens,
        )
    choices = ", ".join(spec.name for spec in PROVIDER_SPECS)
    raise ValueError(f"Unknown provider `{provider}`. Choose from: {choices}.")
