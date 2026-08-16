"""LangChain tool for adding a mixed-responsibility Python aggregation class."""

from __future__ import annotations

import ast

from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult

_AGGREGATOR_NAME = "MixedResponsibilityJunkDrawer"


def _top_level_functions(tree: ast.Module) -> list[str]:
    return [
        statement.name
        for statement in tree.body
        if isinstance(statement, ast.FunctionDef) and not statement.name.startswith("_")
    ]


def mutate_source(code: str) -> MutationResult:
    """Create an unnecessary class that aggregates unrelated top-level functions."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Modules were not merged because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    if any(
        isinstance(statement, ast.ClassDef) and statement.name == _AGGREGATOR_NAME
        for statement in tree.body
    ):
        return MutationResult(
            code=code,
            changed=False,
            summary="Mixed-responsibility aggregation class already exists.",
            edits=[],
            warnings=[],
        )

    functions = _top_level_functions(tree)
    if len(functions) < 2:
        return MutationResult(
            code=code,
            changed=False,
            summary="At least two public top-level functions are required for this source-level merge.",
            edits=[],
            warnings=[
                "True module merging requires the filesystem backend and rollback metadata."
            ],
        )

    selected = functions[:2]
    class_lines = [f"class {_AGGREGATOR_NAME}:"]
    for name in selected:
        class_lines.append(f"    {name} = staticmethod({name})")
    aggregator = ast.parse("\n".join(class_lines)).body[0]
    tree.body.append(aggregator)
    ast.fix_missing_locations(tree)

    return MutationResult(
        code=ast.unparse(tree),
        changed=True,
        summary=f"Aggregated {len(selected)} unrelated function(s) into `{_AGGREGATOR_NAME}`.",
        edits=[
            MutationEdit(
                kind="merge_unrelated_modules",
                before=", ".join(selected),
                after=_AGGREGATOR_NAME,
                line=None,
            )
        ],
        warnings=[
            "This is a source-level stand-in for future workspace-level module merging."
        ],
    )


def merge_unrelated_modules_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def merge_unrelated_modules(code: str) -> str:
    """Add a mixed-responsibility aggregation class for unrelated Python functions."""
    result = mutate_source(code)
    return result.code
