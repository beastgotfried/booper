"""GroqCloud adapter backed by LangChain's ChatGroq integration."""

from __future__ import annotations

import os

from enshittify_providers.base import LangChainModelProvider
from enshittify_providers.capabilities import ProviderCapabilities
from enshittify_providers.errors import (
    ProviderConfigurationError,
    ProviderDependencyError,
)

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_API_KEY_ENV = "GROQ_API_KEY"


def create_groq_provider(
    *,
    api_key: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    timeout: float = 120.0,
    max_retries: int = 2,
    max_tokens: int = 8192,
) -> LangChainModelProvider:
    """Create a tool-calling Groq provider without retaining the plain API key."""
    resolved_key = api_key or os.getenv(GROQ_API_KEY_ENV)
    if not resolved_key:
        raise ProviderConfigurationError(
            f"Groq requires an API key. Set {GROQ_API_KEY_ENV} or pass api_key to the SDK."
        )

    try:
        from langchain_groq import ChatGroq
    except ModuleNotFoundError as error:
        raise ProviderDependencyError(
            "Groq support requires `langchain-groq`; install the project dependencies."
        ) from error

    resolved_model = model or DEFAULT_GROQ_MODEL
    chat_model = ChatGroq(
        model=resolved_model,
        api_key=resolved_key,
        temperature=temperature,
        timeout=timeout,
        max_retries=max_retries,
        max_tokens=max_tokens,
        model_kwargs={"parallel_tool_calls": False},
    )
    return LangChainModelProvider(
        name="groq",
        model=resolved_model,
        chat_model=chat_model,
        capabilities=ProviderCapabilities(
            tool_calling=True,
            structured_output=True,
            token_usage=True,
        ),
    )
