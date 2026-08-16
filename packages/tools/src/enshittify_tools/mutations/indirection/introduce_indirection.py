"""LangChain tool for introducing Python call indirection."""

from __future__ import annotations

import ast

from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


def _collect_names(tree: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def _delegate_name(function_name: str, used_names: set[str]) -> str:
    base = f"_delegate_{function_name}"
    index = 0
    while True:
        candidate = base if index == 0 else f"{base}_{index}"
        if candidate not in used_names:
            return candidate
        index += 1


class _CallIndirectionIntroducer(ast.NodeTransformer):
    def __init__(self) -> None:
        self.target_name: str | None = None
        self.delegate_name: str | None = None
        self.edit: MutationEdit | None = None

    def visit_Call(self, node: ast.Call) -> ast.Call:
        if self.edit is not None:
            return node

        self.generic_visit(node)

        if not isinstance(node.func, ast.Name):
            return node
        if node.func.id.startswith("_delegate_"):
            return node

        self.target_name = node.func.id
        return node

    def replace_target(self, tree: ast.AST, delegate_name: str) -> ast.AST:
        self.delegate_name = delegate_name
        return _CallIndirectionRewriter(
            self.target_name or "", delegate_name, self
        ).visit(tree)


class _CallIndirectionRewriter(ast.NodeTransformer):
    def __init__(
        self,
        target_name: str,
        delegate_name: str,
        owner: _CallIndirectionIntroducer,
    ) -> None:
        self.target_name = target_name
        self.delegate_name = delegate_name
        self.owner = owner

    def visit_Call(self, node: ast.Call) -> ast.Call:
        if self.owner.edit is not None:
            return node

        self.generic_visit(node)

        if isinstance(node.func, ast.Name) and node.func.id == self.target_name:
            original = node.func.id
            node.func = ast.Name(id=self.delegate_name, ctx=ast.Load())
            self.owner.edit = MutationEdit(
                kind="introduce_indirection",
                before=original,
                after=self.delegate_name,
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
    """Wrap one direct function call in an unnecessary delegate function."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Indirection was not introduced because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    finder = _CallIndirectionIntroducer()
    finder.visit(tree)

    if finder.target_name is None:
        return MutationResult(
            code=code,
            changed=False,
            summary="No direct function call was found to wrap.",
            edits=[],
            warnings=[],
        )

    delegate_name = _delegate_name(finder.target_name, _collect_names(tree))
    rewritten_tree = finder.replace_target(tree, delegate_name)

    helper = ast.parse(
        f"""
def {delegate_name}(*args, **kwargs):
    return {finder.target_name}(*args, **kwargs)
"""
    ).body[0]

    rewritten_tree.body.insert(_insertion_index(rewritten_tree), helper)
    ast.fix_missing_locations(rewritten_tree)

    return MutationResult(
        code=ast.unparse(rewritten_tree),
        changed=True,
        summary=f"Introduced delegate `{delegate_name}` for `{finder.target_name}`.",
        edits=[finder.edit] if finder.edit is not None else [],
        warnings=[],
    )


def introduce_indirection_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def introduce_indirection(code: str) -> str:
    """Wrap one direct Python function call in an unnecessary delegate."""
    result = mutate_source(code)
    return result.code
