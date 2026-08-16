"""LangChain tool for replacing named constants with magic values."""

from __future__ import annotations

import ast
import copy
from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult


def _is_magic_constant_assignment(node: ast.stmt) -> tuple[str, ast.Constant] | None:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return None
    target = node.targets[0]
    if not isinstance(target, ast.Name):
        return None
    if not target.id.isupper() or target.id.startswith("_"):
        return None
    if not isinstance(node.value, ast.Constant):
        return None
    if isinstance(node.value.value, (dict, list, set, tuple)):
        return None
    return target.id, node.value


class _ConstantReplacer(ast.NodeTransformer):
    def __init__(self, constants: dict[str, ast.Constant]) -> None:
        self.constants = constants
        self.edits: list[MutationEdit] = []

    def visit_Name(self, node: ast.Name) -> ast.expr:
        if isinstance(node.ctx, ast.Load) and node.id in self.constants:
            replacement = copy.deepcopy(self.constants[node.id])
            ast.copy_location(replacement, node)
            self.edits.append(
                MutationEdit(
                    kind="replace_constant_with_magic_value",
                    before=node.id,
                    after=repr(replacement.value),
                    line=getattr(node, "lineno", None),
                )
            )
            return replacement
        return node


def mutate_source(code: str) -> MutationResult:
    """Replace simple module-level constants with raw literal values."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="No constants were replaced because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    constants: dict[str, ast.Constant] = {}
    constant_assignment_lines: dict[str, int | None] = {}

    for statement in tree.body:
        constant_assignment = _is_magic_constant_assignment(statement)
        if constant_assignment is None:
            continue
        name, value = constant_assignment
        constants[name] = value
        constant_assignment_lines[name] = getattr(statement, "lineno", None)

    if not constants:
        return MutationResult(
            code=code,
            changed=False,
            summary="No simple module-level constants were found.",
            edits=[],
            warnings=[],
        )

    replacer = _ConstantReplacer(constants)
    replaced_tree = replacer.visit(tree)
    ast.fix_missing_locations(replaced_tree)

    replaced_names = {edit.before for edit in replacer.edits}
    if not replaced_names:
        return MutationResult(
            code=code,
            changed=False,
            summary="Constants were found, but no safe references were replaced.",
            edits=[],
            warnings=[],
        )

    replaced_tree.body = [
        statement
        for statement in replaced_tree.body
        if not (
            (constant_assignment := _is_magic_constant_assignment(statement))
            and constant_assignment[0] in replaced_names
        )
    ]

    removal_edits = [
        MutationEdit(
            kind="remove_constant_declaration",
            before=name,
            after=repr(constants[name].value),
            line=constant_assignment_lines.get(name),
        )
        for name in sorted(replaced_names)
    ]

    edits = [*replacer.edits, *removal_edits]

    return MutationResult(
        code=ast.unparse(replaced_tree),
        changed=True,
        summary=f"Replaced {len(replacer.edits)} constant reference(s).",
        edits=edits,
        warnings=[],
    )


def replace_constants_with_magic_values_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def replace_constants_with_magic_values(code: str) -> str:
    """Replace simple named Python constants with raw literal values."""
    result = mutate_source(code)
    return result.code
