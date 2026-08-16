"""LangChain tool for planning Python module fragmentation."""

from __future__ import annotations

import ast
from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


_FRAGMENT_MARKER = "_COHESIVE_MODULE_FRAGMENT_PLAN"


def _top_level_symbols(tree: ast.Module) -> list[str]:
    names: list[str] = []
    for statement in tree.body:
        if isinstance(statement, (ast.FunctionDef, ast.ClassDef)) and not statement.name.startswith("_"):
            names.append(statement.name)
    return names


def mutate_source(code: str) -> MutationResult:
    """Add a source-level fragmentation plan for cohesive top-level symbols."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Module fragmentation was not planned because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    if any(isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == _FRAGMENT_MARKER for target in node.targets) for node in tree.body):
        return MutationResult(
            code=code,
            changed=False,
            summary="A cohesive module fragmentation plan already exists.",
            edits=[],
            warnings=[],
        )

    symbols = _top_level_symbols(tree)
    if len(symbols) < 2:
        return MutationResult(
            code=code,
            changed=False,
            summary="At least two top-level symbols are required for a fragmentation plan.",
            edits=[],
            warnings=["True file splitting requires the filesystem backend and import rewriting."],
        )

    plan = ast.Assign(
        targets=[ast.Name(id=_FRAGMENT_MARKER, ctx=ast.Store())],
        value=ast.List(elts=[ast.Constant(value=symbol) for symbol in symbols[:3]], ctx=ast.Load()),
    )
    tree.body.append(plan)
    ast.fix_missing_locations(tree)

    return MutationResult(
        code=ast.unparse(tree),
        changed=True,
        summary=f"Added a fragmentation plan for {min(len(symbols), 3)} top-level symbol(s).",
        edits=[
            MutationEdit(
                kind="split_cohesive_modules",
                before=", ".join(symbols[:3]),
                after=_FRAGMENT_MARKER,
                line=None,
            )
        ],
        warnings=["This records a source-level split plan; actual file splitting comes with backend integration."],
    )


def split_cohesive_modules_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def split_cohesive_modules(code: str) -> str:
    """Add a Python source-level fragmentation plan for cohesive symbols."""
    result = mutate_source(code)
    return result.code
