"""Provider-neutral LLM integration for enshittify.dev."""

from enshittify_providers.base import (
    LangChainModelProvider,
    ModelProvider,
    wrap_chat_model,
)
from enshittify_providers.capabilities import ProviderCapabilities
from enshittify_providers.errors import (
    ProviderConfigurationError,
    ProviderDependencyError,
    ProviderError,
)
from enshittify_providers.registry import (
    ProviderSpec,
    create_provider,
    list_provider_specs,
)

__all__ = [
    "LangChainModelProvider",
    "ModelProvider",
    "ProviderCapabilities",
    "ProviderConfigurationError",
    "ProviderDependencyError",
    "ProviderError",
    "ProviderSpec",
    "create_provider",
    "list_provider_specs",
    "wrap_chat_model",
]
