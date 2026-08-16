"""LangChain tool for degrading Python error handling."""

from __future__ import annotations

import ast

from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


class _ErrorHandlingDegrader(ast.NodeTransformer):
    def __init__(self) -> None:
        self.edits: list[MutationEdit] = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> ast.ExceptHandler:
        if isinstance(node.type, ast.Name) and node.type.id not in {
            "Exception",
            "BaseException",
        }:
            old_type = node.type.id
            node.type = ast.Name(id="Exception", ctx=ast.Load())
            self.edits.append(
                MutationEdit(
                    kind="broaden_exception_handler",
                    before=old_type,
                    after="Exception",
                    line=getattr(node, "lineno", None),
                )
            )
        self.generic_visit(node)
        return node

    def visit_Raise(self, node: ast.Raise) -> ast.Raise:
        self.generic_visit(node)
        if not isinstance(node.exc, ast.Call) or not node.exc.args:
            return node

        first_arg = node.exc.args[0]
        if not isinstance(first_arg, ast.Constant) or not isinstance(
            first_arg.value, str
        ):
            return node

        old_message = first_arg.value
        node.exc.args[0] = ast.Constant(value="Something went wrong")
        self.edits.append(
            MutationEdit(
                kind="degrade_error_message",
                before=old_message,
                after="Something went wrong",
                line=getattr(node, "lineno", None),
            )
        )
        return node


def mutate_source(code: str) -> MutationResult:
    """Broaden supported exception handlers and weaken error messages."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Error handling was not degraded because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    degrader = _ErrorHandlingDegrader()
    degraded_tree = degrader.visit(tree)
    ast.fix_missing_locations(degraded_tree)

    if not degrader.edits:
        return MutationResult(
            code=code,
            changed=False,
            summary="No supported error-handling pattern was found.",
            edits=[],
            warnings=[],
        )

    return MutationResult(
        code=ast.unparse(degraded_tree),
        changed=True,
        summary=f"Degraded {len(degrader.edits)} error-handling site(s).",
        edits=degrader.edits,
        warnings=[],
    )


def degrade_error_handling_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def degrade_error_handling(code: str) -> str:
    """Broaden Python exception handling and weaken error messages."""
    result = mutate_source(code)
    return result.code
