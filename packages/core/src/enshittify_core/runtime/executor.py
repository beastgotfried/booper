"""Core runtime executor wrappers."""

from __future__ import annotations

from collections.abc import Iterable

from enshittify_tools.result import ToolChainResult

from enshittify_core.runtime.tool_dispatch import run_tool_chain


def execute_mutations(tool_names: Iterable[str], code: str) -> ToolChainResult:
    return run_tool_chain(tool_names, code)
