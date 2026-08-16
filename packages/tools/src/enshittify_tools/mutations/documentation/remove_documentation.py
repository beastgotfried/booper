"""LangChain tool for removing Python documentation from source code."""

from __future__ import annotations

import ast
import io
import tokenize

from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


def _is_docstring_statement(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _count_comments(code: str) -> int:
    comments = 0
    try:
        tokens = tokenize.generate_tokens(io.StringIO(code).readline)
        for token in tokens:
            if token.type != tokenize.COMMENT:
                continue
            if token.start[0] <= 2 and (
                "coding" in token.string or token.string.startswith("#!")
            ):
                continue
            comments += 1
    except tokenize.TokenError:
        return 0
    return comments


class _DocumentationRemover(ast.NodeTransformer):
    def __init__(self) -> None:
        self.edits: list[MutationEdit] = []

    def _strip_body(self, body: list[ast.stmt], owner: str) -> list[ast.stmt]:
        if not body or not _is_docstring_statement(body[0]):
            return body

        docstring = body[0]
        self.edits.append(
            MutationEdit(
                kind="remove_docstring",
                before=owner,
                after="",
                line=getattr(docstring, "lineno", None),
            )
        )
        return body[1:]

    def visit_Module(self, node: ast.Module) -> ast.Module:
        node.body = self._strip_body(node.body, "module")
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.body = self._strip_body(node.body, node.name)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef
    ) -> ast.AsyncFunctionDef:
        node.body = self._strip_body(node.body, node.name)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        node.body = self._strip_body(node.body, node.name)
        self.generic_visit(node)
        return node


def mutate_source(code: str) -> MutationResult:
    """Remove docstrings and comments from Python source code."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Documentation was not removed because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    comment_count = _count_comments(code)
    remover = _DocumentationRemover()
    stripped_tree = remover.visit(tree)
    ast.fix_missing_locations(stripped_tree)

    if not remover.edits and comment_count == 0:
        return MutationResult(
            code=code,
            changed=False,
            summary="No docstrings or comments were found.",
            edits=[],
            warnings=[],
        )

    edits = [
        *remover.edits,
        *[
            MutationEdit(
                kind="remove_comment",
                before="comment",
                after="",
                line=None,
            )
            for _ in range(comment_count)
        ],
    ]

    return MutationResult(
        code=ast.unparse(stripped_tree),
        changed=True,
        summary=f"Removed {len(remover.edits)} docstring(s) and {comment_count} comment(s).",
        edits=edits,
        warnings=[
            "Formatting is normalized because Python AST does not preserve comments."
        ],
    )


def remove_documentation_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def remove_documentation(code: str) -> str:
    """Remove Python comments and docstrings from source code."""
    result = mutate_source(code)
    return result.code
