"""Scripted tool-calling chat models for harness tests."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from pydantic import Field


class ToolCallingFakeChatModel(FakeMessagesListChatModel):
    """A deterministic fake that supports LangChain's tool-binding contract."""

    bound_tool_names: list[str] = Field(default_factory=list, exclude=True)

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Any | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> ToolCallingFakeChatModel:
        del tool_choice, kwargs
        self.bound_tool_names = [
            getattr(tool, "name", getattr(tool, "__name__", "unknown"))
            for tool in tools
        ]
        return self


def tool_call_message(
    name: str,
    arguments: dict[str, Any],
    *,
    call_id: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> AIMessage:
    """Build one scripted AI tool-call response with optional usage metadata."""
    total_tokens = input_tokens + output_tokens
    usage = None
    if total_tokens:
        usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": name,
                "args": arguments,
                "id": call_id,
                "type": "tool_call",
            }
        ],
        usage_metadata=usage,
    )
