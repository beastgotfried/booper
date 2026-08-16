"""LangChain tool for duplicating simple Python logic."""

from __future__ import annotations

import ast
import copy

from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


def _collect_names(tree: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def _duplicate_name(used_names: set[str]) -> str:
    index = 0
    while True:
        candidate = "_duplicated_value" if index == 0 else f"_duplicated_value_{index}"
        if candidate not in used_names:
            return candidate
        index += 1


def _is_simple_logic(node: ast.AST) -> bool:
    return isinstance(node, ast.BinOp) and isinstance(
        node.op,
        (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod),
    )


class _LogicDuplicator(ast.NodeTransformer):
    def __init__(self, duplicate_name: str) -> None:
        self.duplicate_name = duplicate_name
        self.edit: MutationEdit | None = None

    def _visit_body(self, body: list[ast.stmt]) -> list[ast.stmt]:
        if self.edit is not None:
            return body

        new_body: list[ast.stmt] = []
        for statement in body:
            if (
                self.edit is None
                and isinstance(statement, ast.Assign)
                and _is_simple_logic(statement.value)
            ):
                duplicate = ast.Assign(
                    targets=[ast.Name(id=self.duplicate_name, ctx=ast.Store())],
                    value=copy.deepcopy(statement.value),
                )
                ast.copy_location(duplicate, statement)
                new_body.append(duplicate)
                self.edit = MutationEdit(
                    kind="duplicate_logic",
                    before=ast.unparse(statement.value),
                    after=self.duplicate_name,
                    line=getattr(statement, "lineno", None),
                )
            new_body.append(statement)
        return new_body

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.body = self._visit_body(node.body)
        if self.edit is None:
            self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef
    ) -> ast.AsyncFunctionDef:
        node.body = self._visit_body(node.body)
        if self.edit is None:
            self.generic_visit(node)
        return node


def mutate_source(code: str) -> MutationResult:
    """Duplicate a simple expression into an unused intermediate assignment."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Logic was not duplicated because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    duplicate_name = _duplicate_name(_collect_names(tree))
    duplicator = _LogicDuplicator(duplicate_name)
    duplicated_tree = duplicator.visit(tree)
    ast.fix_missing_locations(duplicated_tree)

    if duplicator.edit is None:
        return MutationResult(
            code=code,
            changed=False,
            summary="No simple assignment logic was found to duplicate.",
            edits=[],
            warnings=[],
        )

    return MutationResult(
        code=ast.unparse(duplicated_tree),
        changed=True,
        summary="Duplicated one simple expression into an unused assignment.",
        edits=[duplicator.edit],
        warnings=[],
    )


def duplicate_logic_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def duplicate_logic(code: str) -> str:
    """Duplicate simple Python logic into an unnecessary assignment."""
    result = mutate_source(code)
    return result.code
