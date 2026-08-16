"""Adapter configuration for the local ``codx`` CLI agent."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from typing import Any

from enshittify_protocol import ProviderDescriptor

from enshittify_providers.capabilities import ProviderCapabilities
from enshittify_providers.errors import ProviderConfigurationError

CODX_COMMAND_ENV = "ENSHITTIFY_CODX_COMMAND"
CODX_MODEL_ENV = "ENSHITTIFY_CODX_MODEL"
DEFAULT_CODX_COMMAND = "codx"
DEFAULT_CODX_MODEL = "codex-default"


@dataclass(frozen=True)
class CodxProvider:
    """Configuration for an authorized local Codx CLI wrapper.

    Codx is an external agent runner rather than a LangChain ``BaseChatModel``.
    The core harness connects it through a short-lived stdio MCP server, while
    retaining the same workspace session and action ledger used by the native
    LangChain loop.
    """

    name: str = "codx"
    model: str = DEFAULT_CODX_MODEL
    command: str = DEFAULT_CODX_COMMAND
    timeout: float = 1_800.0
    yolo: bool = True
    capabilities: ProviderCapabilities = field(
        default_factory=lambda: ProviderCapabilities(
            tool_calling=True,
            structured_output=False,
            token_usage=True,
        )
    )
    # The field keeps the provider shape inspectable without pretending Codx is
    # a LangChain chat model. The core runner branches on CodxProvider.
    chat_model: Any = field(default=None, repr=False, compare=False)

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            name=self.name,
            model=self.model,
            capabilities=self.capabilities.names(),
        )


def create_codx_provider(
    *,
    command: str | None = None,
    model: str | None = None,
    timeout: float = 1_800.0,
    yolo: bool = True,
) -> CodxProvider:
    """Resolve the local Codx wrapper without touching its auth state."""
    resolved_command = command or os.getenv(CODX_COMMAND_ENV) or DEFAULT_CODX_COMMAND
    if not resolved_command.strip():
        raise ProviderConfigurationError("Codx command must not be empty.")
    if shutil.which(resolved_command) is None:
        raise ProviderConfigurationError(
            f"Codx command `{resolved_command}` was not found on PATH. "
            f"Set {CODX_COMMAND_ENV} to the authorized wrapper executable."
        )
    if timeout <= 0:
        raise ProviderConfigurationError("Codx timeout must be greater than zero.")
    return CodxProvider(
        model=model or os.getenv(CODX_MODEL_ENV) or DEFAULT_CODX_MODEL,
        command=resolved_command,
        timeout=timeout,
        yolo=yolo,
    )
