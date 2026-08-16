"""LangChain tool for rewriting simple Python control flow."""

from __future__ import annotations

import ast
import copy
from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


def _collect_names(tree: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def _temp_name(used_names: set[str]) -> str:
    index = 0
    while True:
        candidate = "_control_flow_result" if index == 0 else f"_control_flow_result_{index}"
        if candidate not in used_names:
            return candidate
        index += 1


class _ControlFlowRewriter(ast.NodeTransformer):
    def __init__(self, temp_name: str) -> None:
        self.temp_name = temp_name
        self.edit: MutationEdit | None = None

    def _rewrite_body(self, body: list[ast.stmt]) -> list[ast.stmt]:
        if self.edit is not None:
            return body

        new_body: list[ast.stmt] = []
        index = 0
        while index < len(body):
            statement = body[index]
            next_statement = body[index + 1] if index + 1 < len(body) else None

            if (
                self.edit is None
                and isinstance(statement, ast.If)
                and not statement.orelse
                and len(statement.body) == 1
                and isinstance(statement.body[0], ast.Return)
                and isinstance(next_statement, ast.Return)
            ):
                before = f"if {ast.unparse(statement.test)}: return ..."
                initializer = ast.Assign(
                    targets=[ast.Name(id=self.temp_name, ctx=ast.Store())],
                    value=ast.Constant(value=None),
                )
                rewritten_if = ast.If(
                    test=copy.deepcopy(statement.test),
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=self.temp_name, ctx=ast.Store())],
                            value=copy.deepcopy(statement.body[0].value),
                        )
                    ],
                    orelse=[
                        ast.Assign(
                            targets=[ast.Name(id=self.temp_name, ctx=ast.Store())],
                            value=copy.deepcopy(next_statement.value),
                        )
                    ],
                )
                final_return = ast.Return(value=ast.Name(id=self.temp_name, ctx=ast.Load()))

                ast.copy_location(initializer, statement)
                ast.copy_location(rewritten_if, statement)
                ast.copy_location(final_return, next_statement)
                new_body.extend([initializer, rewritten_if, final_return])
                self.edit = MutationEdit(
                    kind="rewrite_control_flow",
                    before=before,
                    after=self.temp_name,
                    line=getattr(statement, "lineno", None),
                )
                index += 2
                continue

            new_body.append(statement)
            index += 1

        return new_body

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.body = self._rewrite_body(node.body)
        if self.edit is None:
            self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        node.body = self._rewrite_body(node.body)
        if self.edit is None:
            self.generic_visit(node)
        return node


def mutate_source(code: str) -> MutationResult:
    """Rewrite a simple if-return/fallback-return pair through a temp variable."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Control flow was not rewritten because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    rewriter = _ControlFlowRewriter(_temp_name(_collect_names(tree)))
    rewritten_tree = rewriter.visit(tree)
    ast.fix_missing_locations(rewritten_tree)

    if rewriter.edit is None:
        return MutationResult(
            code=code,
            changed=False,
            summary="No supported if-return control-flow pattern was found.",
            edits=[],
            warnings=[],
        )

    return MutationResult(
        code=ast.unparse(rewritten_tree),
        changed=True,
        summary="Rewrote one if-return pair through a temporary result variable.",
        edits=[rewriter.edit],
        warnings=[],
    )


def rewrite_control_flow_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def rewrite_control_flow(code: str) -> str:
    """Rewrite simple Python if-return control flow into a less direct shape."""
    result = mutate_source(code)
    return result.code
