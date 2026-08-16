"""LangChain tool for making Python async style less direct."""

from __future__ import annotations

import ast
import copy
from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


def _collect_names(node: ast.AST) -> set[str]:
    return {name.id for name in ast.walk(node) if isinstance(name, ast.Name)}


def _helper_name(used_names: set[str]) -> str:
    index = 0
    while True:
        candidate = "_async_style_delegate" if index == 0 else f"_async_style_delegate_{index}"
        if candidate not in used_names:
            return candidate
        index += 1


class _AsyncStyleConverter(ast.NodeTransformer):
    def __init__(self) -> None:
        self.edit: MutationEdit | None = None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        if self.edit is not None:
            return node

        if (
            len(node.body) != 1
            or not isinstance(node.body[0], ast.Return)
            or not isinstance(node.body[0].value, ast.Await)
        ):
            self.generic_visit(node)
            return node

        awaited_expression = node.body[0].value.value
        helper_name = _helper_name(_collect_names(node))
        helper = ast.AsyncFunctionDef(
            name=helper_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=[ast.Return(value=ast.Await(value=copy.deepcopy(awaited_expression)))],
            decorator_list=[],
            returns=None,
            type_comment=None,
            type_params=[],
        )
        result_assignment = ast.Assign(
            targets=[ast.Name(id="_async_style_result", ctx=ast.Store())],
            value=ast.Await(
                value=ast.Call(
                    func=ast.Name(id=helper_name, ctx=ast.Load()),
                    args=[],
                    keywords=[],
                )
            ),
        )
        final_return = ast.Return(value=ast.Name(id="_async_style_result", ctx=ast.Load()))

        ast.copy_location(helper, node.body[0])
        ast.copy_location(result_assignment, node.body[0])
        ast.copy_location(final_return, node.body[0])

        node.body = [helper, result_assignment, final_return]
        self.edit = MutationEdit(
            kind="convert_async_style",
            before=f"return await {ast.unparse(awaited_expression)}",
            after=f"await {helper_name}()",
            line=getattr(node.body[0], "lineno", None),
        )
        return node


def mutate_source(code: str) -> MutationResult:
    """Wrap a direct async return-await in an unnecessary nested coroutine."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Async style was not converted because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    converter = _AsyncStyleConverter()
    converted_tree = converter.visit(tree)
    ast.fix_missing_locations(converted_tree)

    if converter.edit is None:
        return MutationResult(
            code=code,
            changed=False,
            summary="No direct async return-await pattern was found.",
            edits=[],
            warnings=[],
        )

    return MutationResult(
        code=ast.unparse(converted_tree),
        changed=True,
        summary="Converted one direct async return-await into a delegated style.",
        edits=[converter.edit],
        warnings=[],
    )


def convert_async_style_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def convert_async_style(code: str) -> str:
    """Convert direct Python async style into a less direct nested coroutine style."""
    result = mutate_source(code)
    return result.code
