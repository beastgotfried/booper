"""LangChain tool for introducing Python alias chains."""

from __future__ import annotations

import ast
import copy

from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


def _collect_names(tree: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def _alias_names(used_names: set[str]) -> tuple[str, str]:
    index = 0
    while True:
        first = "_alias_value" if index == 0 else f"_alias_value_{index}"
        second = "_alias_value_next" if index == 0 else f"_alias_value_next_{index}"
        if first not in used_names and second not in used_names:
            return first, second
        index += 1


class _AliasChainIntroducer(ast.NodeTransformer):
    def __init__(self, first_alias: str, second_alias: str) -> None:
        self.first_alias = first_alias
        self.second_alias = second_alias
        self.edit: MutationEdit | None = None

    def _chain_for_value(
        self, value: ast.Name, line: int | None
    ) -> tuple[list[ast.stmt], ast.Name]:
        first_assignment = ast.Assign(
            targets=[ast.Name(id=self.first_alias, ctx=ast.Store())],
            value=copy.deepcopy(value),
        )
        second_assignment = ast.Assign(
            targets=[ast.Name(id=self.second_alias, ctx=ast.Store())],
            value=ast.Name(id=self.first_alias, ctx=ast.Load()),
        )
        self.edit = MutationEdit(
            kind="introduce_alias_chain",
            before=value.id,
            after=f"{self.first_alias} -> {self.second_alias}",
            line=line,
        )
        return [first_assignment, second_assignment], ast.Name(
            id=self.second_alias, ctx=ast.Load()
        )

    def _visit_body(self, body: list[ast.stmt]) -> list[ast.stmt]:
        if self.edit is not None:
            return body

        new_body: list[ast.stmt] = []
        for statement in body:
            if (
                self.edit is None
                and isinstance(statement, ast.Assign)
                and isinstance(statement.value, ast.Name)
            ):
                chain, replacement = self._chain_for_value(
                    statement.value, getattr(statement, "lineno", None)
                )
                statement.value = replacement
                new_body.extend(chain)
                new_body.append(statement)
                continue

            if (
                self.edit is None
                and isinstance(statement, ast.Return)
                and isinstance(statement.value, ast.Name)
            ):
                chain, replacement = self._chain_for_value(
                    statement.value, getattr(statement, "lineno", None)
                )
                statement.value = replacement
                new_body.extend(chain)
                new_body.append(statement)
                continue

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
    """Introduce a two-step alias chain before one simple use."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Alias chains were not introduced because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    first_alias, second_alias = _alias_names(_collect_names(tree))
    introducer = _AliasChainIntroducer(first_alias, second_alias)
    rewritten_tree = introducer.visit(tree)
    ast.fix_missing_locations(rewritten_tree)

    if introducer.edit is None:
        return MutationResult(
            code=code,
            changed=False,
            summary="No simple name use was found for an alias chain.",
            edits=[],
            warnings=[],
        )

    return MutationResult(
        code=ast.unparse(rewritten_tree),
        changed=True,
        summary="Introduced one two-step alias chain.",
        edits=[introducer.edit],
        warnings=[],
    )


def introduce_alias_chains_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def introduce_alias_chains(code: str) -> str:
    """Introduce a redundant Python alias chain before a simple name use."""
    result = mutate_source(code)
    return result.code
