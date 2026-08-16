"""Small executor helpers for invoking registered tools."""

from __future__ import annotations

import ast
from collections.abc import Iterable
from importlib import import_module

from enshittify_tools.registry import ToolRegistry, create_default_registry
from enshittify_tools.result import MutationResult, ToolChainResult, ToolRun


def invoke_tool(name: str, code: str, registry: ToolRegistry | None = None) -> str:
    active_registry = registry or create_default_registry()
    tool = active_registry.get_tool(name)
    return tool.invoke({"code": code})


def execute_tool(
    name: str, code: str, registry: ToolRegistry | None = None
) -> MutationResult:
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
    continue_on_error: bool = False,
) -> ToolChainResult:
    active_registry = registry or create_default_registry()
    ordered_names = list(names)
    for name in ordered_names:
        active_registry.get_spec(name)

    current_code = code
    runs: list[ToolRun] = []

    for name in ordered_names:
        try:
            result = execute_tool(name, current_code, active_registry)
        except Exception as error:
            if not continue_on_error:
                raise
            result = MutationResult(
                code=current_code,
                changed=False,
                summary=f"Tool `{name}` failed and was skipped.",
                edits=[],
                warnings=[f"{type(error).__name__}: {error}"],
            )

        if validate_python:
            try:
                ast.parse(result.code)
            except SyntaxError as error:
                message = (
                    f"Tool `{name}` produced invalid Python on line "
                    f"{error.lineno}: {error.msg}"
                )
                if not continue_on_error:
                    raise ValueError(message) from error
                result = MutationResult(
                    code=current_code,
                    changed=False,
                    summary=f"Tool `{name}` produced invalid Python and was skipped.",
                    edits=[],
                    warnings=[message],
                )

        runs.append(ToolRun(name=name, result=result))
        current_code = result.code

    return ToolChainResult(code=current_code, runs=runs)
