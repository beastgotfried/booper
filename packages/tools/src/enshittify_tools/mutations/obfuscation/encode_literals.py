"""LangChain tool for encoding obvious Python literals."""

from __future__ import annotations

import ast
from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


def _is_docstring_statement(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _string_join_expression(value: str) -> ast.expr:
    return ast.Call(
        func=ast.Attribute(value=ast.Constant(value=""), attr="join", ctx=ast.Load()),
        args=[
            ast.List(
                elts=[ast.Constant(value=character) for character in value],
                ctx=ast.Load(),
            )
        ],
        keywords=[],
    )


def _integer_expression(value: int) -> ast.expr:
    if value == 0:
        return ast.BinOp(
            left=ast.Constant(value=1),
            op=ast.Sub(),
            right=ast.Constant(value=1),
        )

    return ast.BinOp(
        left=ast.Constant(value=value - 1),
        op=ast.Add(),
        right=ast.Constant(value=1),
    )


class _LiteralEncoder(ast.NodeTransformer):
    def __init__(self) -> None:
        self.edits: list[MutationEdit] = []

    def _visit_body(self, body: list[ast.stmt]) -> list[ast.stmt]:
        if body and _is_docstring_statement(body[0]):
            return [body[0], *[self.visit(statement) for statement in body[1:]]]
        return [self.visit(statement) for statement in body]

    def visit_Module(self, node: ast.Module) -> ast.Module:
        node.body = self._visit_body(node.body)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.args = self.visit(node.args)
        node.decorator_list = [self.visit(decorator) for decorator in node.decorator_list]
        node.returns = self.visit(node.returns) if node.returns is not None else None
        node.body = self._visit_body(node.body)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        node.args = self.visit(node.args)
        node.decorator_list = [self.visit(decorator) for decorator in node.decorator_list]
        node.returns = self.visit(node.returns) if node.returns is not None else None
        node.body = self._visit_body(node.body)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        node.bases = [self.visit(base) for base in node.bases]
        node.keywords = [self.visit(keyword) for keyword in node.keywords]
        node.decorator_list = [self.visit(decorator) for decorator in node.decorator_list]
        node.body = self._visit_body(node.body)
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.expr:
        if isinstance(node.value, str) and node.value:
            replacement = _string_join_expression(node.value)
        elif isinstance(node.value, int) and not isinstance(node.value, bool):
            replacement = _integer_expression(node.value)
        else:
            return node

        ast.copy_location(replacement, node)
        self.edits.append(
            MutationEdit(
                kind="encode_literal",
                before=repr(node.value),
                after=ast.unparse(replacement),
                line=getattr(node, "lineno", None),
            )
        )
        return replacement


def mutate_source(code: str) -> MutationResult:
    """Encode selected Python literals as less direct expressions."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="No literals were encoded because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    encoder = _LiteralEncoder()
    encoded_tree = encoder.visit(tree)
    ast.fix_missing_locations(encoded_tree)

    if not encoder.edits:
        return MutationResult(
            code=code,
            changed=False,
            summary="No supported literal candidates were found.",
            edits=[],
            warnings=[],
        )

    return MutationResult(
        code=ast.unparse(encoded_tree),
        changed=True,
        summary=f"Encoded {len(encoder.edits)} literal(s).",
        edits=encoder.edits,
        warnings=[],
    )


def encode_literals_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def encode_literals(code: str) -> str:
    """Replace obvious Python literals with equivalent encoded expressions."""
    result = mutate_source(code)
    return result.code
