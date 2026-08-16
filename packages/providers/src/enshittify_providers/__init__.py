"""Provider-neutral LLM integration for enshittify.dev."""

from enshittify_providers.adapters.codx import (
    CODX_COMMAND_ENV,
    CODX_MODEL_ENV,
    DEFAULT_CODX_COMMAND,
    DEFAULT_CODX_MODEL,
    CodxProvider,
    create_codx_provider,
)
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
    "CODX_COMMAND_ENV",
    "CODX_MODEL_ENV",
    "DEFAULT_CODX_COMMAND",
    "DEFAULT_CODX_MODEL",
    "CodxProvider",
    "LangChainModelProvider",
    "ModelProvider",
    "ProviderCapabilities",
    "ProviderConfigurationError",
    "ProviderDependencyError",
    "ProviderError",
    "ProviderSpec",
    "create_codx_provider",
    "create_provider",
    "list_provider_specs",
    "wrap_chat_model",
]
