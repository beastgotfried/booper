"""Dispatch helpers for executing registered mutation tools."""

from __future__ import annotations

from collections.abc import Iterable

from enshittify_tools.executor import execute_tool_chain
from enshittify_tools.result import ToolChainResult


def run_tool_chain(
    tool_names: Iterable[str],
    code: str,
    *,
    continue_on_error: bool = False,
) -> ToolChainResult:
    return execute_tool_chain(tool_names, code, continue_on_error=continue_on_error)
