"""LangChain tool for collapsing Python source formatting."""

from __future__ import annotations

import ast
from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


def _collapse_lines(code: str) -> tuple[str, list[MutationEdit]]:
    collapsed_lines: list[str] = []
    edits: list[MutationEdit] = []
    blank_line_count = 0
    trailing_space_count = 0

    for line_number, line in enumerate(code.splitlines(), start=1):
        trimmed = line.rstrip()
        if trimmed != line:
            trailing_space_count += 1

        if not trimmed.strip():
            blank_line_count += 1
            continue

        collapsed_lines.append(trimmed)

    if blank_line_count:
        edits.append(
            MutationEdit(
                kind="remove_blank_lines",
                before=str(blank_line_count),
                after="0",
                line=None,
            )
        )

    if trailing_space_count:
        edits.append(
            MutationEdit(
                kind="remove_trailing_whitespace",
                before=str(trailing_space_count),
                after="0",
                line=None,
            )
        )

    collapsed = "\n".join(collapsed_lines)
    if code.endswith("\n") and collapsed:
        collapsed += "\n"

    return collapsed, edits


def mutate_source(code: str) -> MutationResult:
    """Remove blank lines and trailing whitespace while preserving syntax."""
    try:
        ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Formatting was not collapsed because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    collapsed, edits = _collapse_lines(code)

    if collapsed == code:
        return MutationResult(
            code=code,
            changed=False,
            summary="No collapsible formatting was found.",
            edits=[],
            warnings=[],
        )

    try:
        ast.parse(collapsed)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Formatting collapse was rejected because it produced invalid syntax.",
            edits=[],
            warnings=[f"Generated SyntaxError on line {error.lineno}: {error.msg}"],
        )

    return MutationResult(
        code=collapsed,
        changed=True,
        summary="Collapsed blank lines and trailing whitespace.",
        edits=edits,
        warnings=[],
    )


def collapse_formatting_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def collapse_formatting(code: str) -> str:
    """Collapse safe Python formatting whitespace."""
    result = mutate_source(code)
    return result.code
