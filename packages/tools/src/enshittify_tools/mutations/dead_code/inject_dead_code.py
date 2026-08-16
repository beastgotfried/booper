"""LangChain tool for injecting inert Python dead code."""

from __future__ import annotations

import ast

from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult

_GENERATED_HELPER = "_unused_legacy_compatibility_path"


def _top_level_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(statement.name)
        elif isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _insertion_index(tree: ast.Module) -> int:
    index = 0
    if tree.body and isinstance(tree.body[0], ast.Expr):
        value = tree.body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            index = 1

    while index < len(tree.body):
        statement = tree.body[index]
        if isinstance(statement, (ast.Import, ast.ImportFrom)):
            index += 1
            continue
        break

    return index


def mutate_source(code: str) -> MutationResult:
    """Insert a bounded, inert helper function into Python source code."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Dead code was not injected because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    if _GENERATED_HELPER in _top_level_names(tree):
        return MutationResult(
            code=code,
            changed=False,
            summary="Generated dead-code helper already exists.",
            edits=[],
            warnings=[],
        )

    helper = ast.parse(
        f"""
def {_GENERATED_HELPER}(value=None):
    if False:
        return value
    return None
"""
    ).body[0]

    index = _insertion_index(tree)
    tree.body.insert(index, helper)
    ast.fix_missing_locations(tree)

    return MutationResult(
        code=ast.unparse(tree),
        changed=True,
        summary=f"Injected inert helper `{_GENERATED_HELPER}`.",
        edits=[
            MutationEdit(
                kind="inject_dead_code",
                before="",
                after=_GENERATED_HELPER,
                line=index + 1,
            )
        ],
        warnings=[],
    )


def inject_dead_code_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def inject_dead_code(code: str) -> str:
    """Insert bounded inert Python dead code."""
    result = mutate_source(code)
    return result.code
