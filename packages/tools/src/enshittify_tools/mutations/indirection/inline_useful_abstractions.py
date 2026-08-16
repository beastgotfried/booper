"""LangChain tool for inlining useful Python abstractions."""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass

from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


@dataclass(frozen=True)
class _InlineCandidate:
    name: str
    parameters: list[str]
    expression: ast.expr


def _candidate_from_function(node: ast.FunctionDef) -> _InlineCandidate | None:
    if (
        node.decorator_list
        or len(node.body) != 1
        or not isinstance(node.body[0], ast.Return)
    ):
        return None
    if (
        node.args.vararg
        or node.args.kwarg
        or node.args.kwonlyargs
        or node.args.posonlyargs
    ):
        return None
    if node.body[0].value is None:
        return None
    parameters = [argument.arg for argument in node.args.args]
    return _InlineCandidate(
        name=node.name, parameters=parameters, expression=node.body[0].value
    )


class _ParameterSubstituter(ast.NodeTransformer):
    def __init__(self, replacements: dict[str, ast.expr]) -> None:
        self.replacements = replacements

    def visit_Name(self, node: ast.Name) -> ast.expr:
        if isinstance(node.ctx, ast.Load) and node.id in self.replacements:
            replacement = copy.deepcopy(self.replacements[node.id])
            ast.copy_location(replacement, node)
            return replacement
        return node


class _AbstractionInliner(ast.NodeTransformer):
    def __init__(self, candidates: dict[str, _InlineCandidate]) -> None:
        self.candidates = candidates
        self.edit: MutationEdit | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        return node

    def visit_Call(self, node: ast.Call) -> ast.expr:
        if self.edit is not None:
            return node

        self.generic_visit(node)

        if not isinstance(node.func, ast.Name) or node.keywords:
            return node

        candidate = self.candidates.get(node.func.id)
        if candidate is None or len(node.args) != len(candidate.parameters):
            return node

        replacements = dict(zip(candidate.parameters, node.args, strict=True))
        inlined = _ParameterSubstituter(replacements).visit(
            copy.deepcopy(candidate.expression)
        )
        ast.copy_location(inlined, node)
        self.edit = MutationEdit(
            kind="inline_useful_abstraction",
            before=f"{candidate.name}(...)",
            after=ast.unparse(inlined),
            line=getattr(node, "lineno", None),
        )
        return inlined


def mutate_source(code: str) -> MutationResult:
    """Inline one simple pure helper function call."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="A useful abstraction was not inlined because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    candidates = {
        candidate.name: candidate
        for statement in tree.body
        if isinstance(statement, ast.FunctionDef)
        and (candidate := _candidate_from_function(statement)) is not None
    }

    if not candidates:
        return MutationResult(
            code=code,
            changed=False,
            summary="No simple pure helper functions were found to inline.",
            edits=[],
            warnings=[],
        )

    inliner = _AbstractionInliner(candidates)
    inlined_tree = inliner.visit(tree)
    ast.fix_missing_locations(inlined_tree)

    if inliner.edit is None:
        return MutationResult(
            code=code,
            changed=False,
            summary="Helper candidates were found, but no supported call site was found.",
            edits=[],
            warnings=[],
        )

    return MutationResult(
        code=ast.unparse(inlined_tree),
        changed=True,
        summary="Inlined one simple helper call.",
        edits=[inliner.edit],
        warnings=[],
    )


def inline_useful_abstractions_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def inline_useful_abstractions(code: str) -> str:
    """Inline one simple Python helper function call into its call site."""
    result = mutate_source(code)
    return result.code
