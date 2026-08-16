"""LangChain tool for inflating Python imports."""

from __future__ import annotations

import ast

from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult

_IMPORT_ALIAS = "_enshittify_collections"


def _has_inflated_import(tree: ast.Module) -> bool:
    for statement in tree.body:
        if not isinstance(statement, ast.Import):
            continue
        for alias in statement.names:
            if alias.name == "collections" and alias.asname == _IMPORT_ALIAS:
                return True
    return False


def _insertion_index(tree: ast.Module) -> int:
    index = 0
    if tree.body and isinstance(tree.body[0], ast.Expr):
        value = tree.body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            index = 1
    while index < len(tree.body) and isinstance(
        tree.body[index], (ast.Import, ast.ImportFrom)
    ):
        index += 1
    return index


def mutate_source(code: str) -> MutationResult:
    """Add one redundant standard-library import to inflate import surface area."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Dependencies were not inflated because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    if _has_inflated_import(tree):
        return MutationResult(
            code=code,
            changed=False,
            summary="The redundant dependency import already exists.",
            edits=[],
            warnings=[],
        )

    import_node = ast.Import(
        names=[ast.alias(name="collections", asname=_IMPORT_ALIAS)]
    )
    index = _insertion_index(tree)
    tree.body.insert(index, import_node)
    ast.fix_missing_locations(tree)

    return MutationResult(
        code=ast.unparse(tree),
        changed=True,
        summary="Added one redundant standard-library import.",
        edits=[
            MutationEdit(
                kind="inflate_dependencies",
                before="",
                after=f"import collections as {_IMPORT_ALIAS}",
                line=index + 1,
            )
        ],
        warnings=[
            "Package manifests are intentionally not modified by this source-only tool."
        ],
    )


def inflate_dependencies_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def inflate_dependencies(code: str) -> str:
    """Add a redundant Python import without changing package manifests."""
    result = mutate_source(code)
    return result.code
