"""LangChain tool for extracting trivial Python helpers."""

from __future__ import annotations

import ast

from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


def _collect_names(tree: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def _ordered_names(expression: ast.AST) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for node in ast.walk(expression):
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id not in seen
        ):
            names.append(node.id)
            seen.add(node.id)
    return names


def _helper_name(used_names: set[str]) -> str:
    index = 0
    while True:
        candidate = "_trivial_helper" if index == 0 else f"_trivial_helper_{index}"
        if candidate not in used_names:
            return candidate
        index += 1


def _is_extractable_expression(node: ast.AST) -> bool:
    return isinstance(node, ast.BinOp) and isinstance(
        node.op,
        (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod),
    )


class _TrivialHelperExtractor(ast.NodeTransformer):
    def __init__(self, helper_name: str) -> None:
        self.helper_name = helper_name
        self.helper: ast.FunctionDef | None = None
        self.edit: MutationEdit | None = None

    def visit_Assign(self, node: ast.Assign) -> ast.Assign:
        if self.edit is not None or not _is_extractable_expression(node.value):
            return node

        parameters = _ordered_names(node.value)
        if not parameters:
            return node

        expression_source = ast.unparse(node.value)
        helper_source = (
            f"def {self.helper_name}({', '.join(parameters)}):\n"
            f"    return {expression_source}\n"
        )
        self.helper = ast.parse(helper_source).body[0]
        node.value = ast.Call(
            func=ast.Name(id=self.helper_name, ctx=ast.Load()),
            args=[ast.Name(id=name, ctx=ast.Load()) for name in parameters],
            keywords=[],
        )
        self.edit = MutationEdit(
            kind="extract_trivial_helper",
            before=expression_source,
            after=self.helper_name,
            line=getattr(node, "lineno", None),
        )
        return node


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
    """Extract one simple expression into an unnecessary helper function."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="A helper was not extracted because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    extractor = _TrivialHelperExtractor(_helper_name(_collect_names(tree)))
    rewritten_tree = extractor.visit(tree)

    if extractor.helper is None or extractor.edit is None:
        return MutationResult(
            code=code,
            changed=False,
            summary="No simple assignment expression was found to extract.",
            edits=[],
            warnings=[],
        )

    rewritten_tree.body.insert(_insertion_index(rewritten_tree), extractor.helper)
    ast.fix_missing_locations(rewritten_tree)

    return MutationResult(
        code=ast.unparse(rewritten_tree),
        changed=True,
        summary=f"Extracted one trivial helper `{extractor.helper_name}`.",
        edits=[extractor.edit],
        warnings=[],
    )


def extract_trivial_helpers_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def extract_trivial_helpers(code: str) -> str:
    """Extract a simple Python expression into an unnecessary helper."""
    result = mutate_source(code)
    return result.code
