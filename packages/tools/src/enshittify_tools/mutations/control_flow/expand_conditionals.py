"""LangChain tool for expanding compact Python conditionals."""

from __future__ import annotations

import ast
import copy
from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


def _is_safe_operand(node: ast.expr) -> bool:
    return isinstance(node, (ast.Name, ast.Constant))


def _expand_bool_return(node: ast.Return) -> list[ast.stmt] | None:
    value = node.value
    if not isinstance(value, ast.BoolOp) or len(value.values) != 2:
        return None

    left, right = value.values
    if not _is_safe_operand(left) or not _is_safe_operand(right):
        return None

    if isinstance(value.op, ast.And):
        expanded = ast.If(
            test=copy.deepcopy(left),
            body=[ast.Return(value=copy.deepcopy(right))],
            orelse=[ast.Return(value=copy.deepcopy(left))],
        )
    elif isinstance(value.op, ast.Or):
        expanded = ast.If(
            test=copy.deepcopy(left),
            body=[ast.Return(value=copy.deepcopy(left))],
            orelse=[ast.Return(value=copy.deepcopy(right))],
        )
    else:
        return None

    ast.copy_location(expanded, node)
    return [expanded]


class _ConditionalExpander(ast.NodeTransformer):
    def __init__(self) -> None:
        self.edit: MutationEdit | None = None

    def visit_Return(self, node: ast.Return) -> ast.Return | list[ast.stmt]:
        if self.edit is not None:
            return node

        expanded = _expand_bool_return(node)
        if expanded is None:
            return node

        self.edit = MutationEdit(
            kind="expand_conditional",
            before=ast.unparse(node),
            after=ast.unparse(expanded[0]),
            line=getattr(node, "lineno", None),
        )
        return expanded


def mutate_source(code: str) -> MutationResult:
    """Expand one simple boolean return into an explicit branch."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Conditionals were not expanded because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    expander = _ConditionalExpander()
    expanded_tree = expander.visit(tree)
    ast.fix_missing_locations(expanded_tree)

    if expander.edit is None:
        return MutationResult(
            code=code,
            changed=False,
            summary="No supported compact boolean return was found.",
            edits=[],
            warnings=[],
        )

    return MutationResult(
        code=ast.unparse(expanded_tree),
        changed=True,
        summary="Expanded one compact boolean return.",
        edits=[expander.edit],
        warnings=[],
    )


def expand_conditionals_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def expand_conditionals(code: str) -> str:
    """Expand simple Python boolean returns into explicit branches."""
    result = mutate_source(code)
    return result.code
