"""Built-in model-provider adapters."""

from enshittify_providers.adapters.codx import (
    CODX_COMMAND_ENV,
    CODX_MODEL_ENV,
    DEFAULT_CODX_COMMAND,
    DEFAULT_CODX_MODEL,
    CodxProvider,
    create_codx_provider,
)
from enshittify_providers.adapters.groq import (
    DEFAULT_GROQ_MODEL,
    GROQ_API_KEY_ENV,
    create_groq_provider,
)

__all__ = [
    "CODX_COMMAND_ENV",
    "CODX_MODEL_ENV",
    "DEFAULT_CODX_COMMAND",
    "DEFAULT_CODX_MODEL",
    "DEFAULT_GROQ_MODEL",
    "GROQ_API_KEY_ENV",
    "CodxProvider",
    "create_codx_provider",
    "create_groq_provider",
]
