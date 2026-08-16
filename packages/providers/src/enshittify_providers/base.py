"""Provider-neutral wrappers around LangChain chat models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from enshittify_protocol import ProviderDescriptor
from langchain_core.language_models.chat_models import BaseChatModel

from enshittify_providers.capabilities import ProviderCapabilities


@runtime_checkable
class ModelProvider(Protocol):
    """The small provider surface required by the harness."""

    name: str
    model: str
    chat_model: BaseChatModel
    capabilities: ProviderCapabilities

    def descriptor(self) -> ProviderDescriptor: ...


@dataclass
class LangChainModelProvider:
    """Adapt any LangChain chat model to the enshittify.dev provider contract."""

    name: str
    model: str
    chat_model: BaseChatModel
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            name=self.name,
            model=self.model,
            capabilities=self.capabilities.names(),
        )


def wrap_chat_model(
    chat_model: BaseChatModel,
    *,
    name: str = "custom",
    model: str | None = None,
    capabilities: ProviderCapabilities | None = None,
) -> LangChainModelProvider:
    """Wrap a caller-supplied LangChain model for provider hot swapping."""
    resolved_model = model or _read_model_name(chat_model)
    return LangChainModelProvider(
        name=name,
        model=resolved_model,
        chat_model=chat_model,
        capabilities=capabilities or ProviderCapabilities(),
    )


def _read_model_name(chat_model: BaseChatModel) -> str:
    for attribute in ("model_name", "model"):
        value: Any = getattr(chat_model, attribute, None)
        if isinstance(value, str) and value:
            return value
    return type(chat_model).__name__
