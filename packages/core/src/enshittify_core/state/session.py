"""State contracts for harness runs."""

from __future__ import annotations

from typing import NotRequired, TypedDict

from enshittify_tools.result import ToolChainResult


class HarnessState(TypedDict):
    code: str
    tool_names: list[str]
    result: NotRequired[ToolChainResult]
    warnings: NotRequired[list[str]]
