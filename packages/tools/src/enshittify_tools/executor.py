"""Small executor helpers for invoking registered tools."""

from __future__ import annotations

import ast
from importlib import import_module
from collections.abc import Iterable

from enshittify_tools.registry import ToolRegistry, create_default_registry
from enshittify_tools.result import MutationResult, ToolChainResult, ToolRun


def invoke_tool(name: str, code: str, registry: ToolRegistry | None = None) -> str:
    active_registry = registry or create_default_registry()
    tool = active_registry.get_tool(name)
    return tool.invoke({"code": code})


def execute_tool(name: str, code: str, registry: ToolRegistry | None = None) -> MutationResult:
    active_registry = registry or create_default_registry()
    spec = active_registry.get_spec(name)
    module = import_module(spec.module)
    return module.mutate_source(code)


def execute_tool_chain(
    names: Iterable[str],
    code: str,
    registry: ToolRegistry | None = None,
    *,
    validate_python: bool = True,
) -> ToolChainResult:
    active_registry = registry or create_default_registry()
    current_code = code
    runs: list[ToolRun] = []

    for name in names:
        result = execute_tool(name, current_code, active_registry)

        if validate_python:
            try:
                ast.parse(result.code)
            except SyntaxError as error:
                raise ValueError(
                    f"Tool `{name}` produced invalid Python on line {error.lineno}: {error.msg}"
                ) from error

        runs.append(ToolRun(name=name, result=result))
        current_code = result.code

    return ToolChainResult(code=current_code, runs=runs)
