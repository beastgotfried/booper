"""LangChain tool for weakening Python type annotations."""

from __future__ import annotations

import ast
from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


def _is_any_annotation(annotation: ast.expr | None) -> bool:
    return isinstance(annotation, ast.Name) and annotation.id == "Any"


def _has_any_import(tree: ast.Module) -> bool:
    for statement in tree.body:
        if isinstance(statement, ast.ImportFrom) and statement.module == "typing":
            if any(alias.name == "Any" for alias in statement.names):
                return True
    return False


def _import_insertion_index(tree: ast.Module) -> int:
    index = 0
    if tree.body and isinstance(tree.body[0], ast.Expr):
        value = tree.body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            index = 1

    while index < len(tree.body):
        statement = tree.body[index]
        if isinstance(statement, ast.ImportFrom) and statement.module == "__future__":
            index += 1
            continue
        break
    return index


class _TypeWeakener(ast.NodeTransformer):
    def __init__(self) -> None:
        self.edits: list[MutationEdit] = []

    def _weaken_annotation(self, annotation: ast.expr | None, line: int | None, kind: str) -> ast.expr | None:
        if annotation is None or _is_any_annotation(annotation):
            return annotation

        self.edits.append(
            MutationEdit(
                kind=kind,
                before=ast.unparse(annotation),
                after="Any",
                line=line,
            )
        )
        return ast.Name(id="Any", ctx=ast.Load())

    def visit_arg(self, node: ast.arg) -> ast.arg:
        if node.arg not in {"self", "cls"}:
            node.annotation = self._weaken_annotation(
                node.annotation,
                getattr(node, "lineno", None),
                "weaken_argument_type",
            )
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        node.returns = self._weaken_annotation(
            node.returns,
            getattr(node, "lineno", None),
            "weaken_return_type",
        )
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        self.generic_visit(node)
        node.returns = self._weaken_annotation(
            node.returns,
            getattr(node, "lineno", None),
            "weaken_return_type",
        )
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AnnAssign:
        self.generic_visit(node)
        node.annotation = self._weaken_annotation(
            node.annotation,
            getattr(node, "lineno", None),
            "weaken_variable_type",
        )
        return node


def mutate_source(code: str) -> MutationResult:
    """Replace selected Python annotations with `Any`."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Types were not weakened because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    weakener = _TypeWeakener()
    weakened_tree = weakener.visit(tree)

    if not weakener.edits:
        return MutationResult(
            code=code,
            changed=False,
            summary="No type annotations were found to weaken.",
            edits=[],
            warnings=[],
        )

    if not _has_any_import(weakened_tree):
        any_import = ast.ImportFrom(
            module="typing",
            names=[ast.alias(name="Any")],
            level=0,
        )
        weakened_tree.body.insert(_import_insertion_index(weakened_tree), any_import)

    ast.fix_missing_locations(weakened_tree)

    return MutationResult(
        code=ast.unparse(weakened_tree),
        changed=True,
        summary=f"Weakened {len(weakener.edits)} type annotation(s).",
        edits=weakener.edits,
        warnings=[],
    )


def weaken_types_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def weaken_types(code: str) -> str:
    """Replace Python type annotations with weaker `Any` annotations."""
    result = mutate_source(code)
    return result.code
