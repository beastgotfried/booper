"""LangChain tool for spreading Python configuration."""

from __future__ import annotations

import ast
import copy
import re

from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult

_SECRET_WORDS = {"secret", "token", "password", "credential", "key"}


def _safe_config_name(prefix: str, key: str) -> str:
    suffix = re.sub(r"[^0-9a-zA-Z_]+", "_", key).strip("_").upper()
    if not suffix:
        suffix = "VALUE"
    if suffix[0].isdigit():
        suffix = f"VALUE_{suffix}"
    return f"{prefix}_{suffix}"


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(word in lowered for word in _SECRET_WORDS)


def _config_assignment(statement: ast.stmt) -> tuple[str, ast.Dict] | None:
    if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
        return None
    target = statement.targets[0]
    if not isinstance(target, ast.Name) or "CONFIG" not in target.id.upper():
        return None
    if not isinstance(statement.value, ast.Dict):
        return None
    return target.id, statement.value


def mutate_source(code: str) -> MutationResult:
    """Split safe entries from one config dictionary into separate constants."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="Configuration was not spread because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    edits: list[MutationEdit] = []
    warnings: list[str] = []
    changed = False
    new_body: list[ast.stmt] = []

    for statement in tree.body:
        if changed:
            new_body.append(statement)
            continue

        assignment = _config_assignment(statement)
        if assignment is None:
            new_body.append(statement)
            continue

        config_name, config_dict = assignment
        prefix = config_name.upper()
        extracted_assignments: list[ast.Assign] = []

        for index, key_node in enumerate(config_dict.keys):
            value_node = config_dict.values[index]
            if not isinstance(key_node, ast.Constant) or not isinstance(
                key_node.value, str
            ):
                continue
            if _is_secret_key(key_node.value):
                warnings.append(f"Skipped secret-like config key `{key_node.value}`.")
                continue

            constant_name = _safe_config_name(prefix, key_node.value)
            extracted_assignments.append(
                ast.Assign(
                    targets=[ast.Name(id=constant_name, ctx=ast.Store())],
                    value=copy.deepcopy(value_node),
                )
            )
            config_dict.values[index] = ast.Name(id=constant_name, ctx=ast.Load())
            edits.append(
                MutationEdit(
                    kind="spread_configuration",
                    before=f"{config_name}[{key_node.value!r}]",
                    after=constant_name,
                    line=getattr(statement, "lineno", None),
                )
            )

        if extracted_assignments:
            new_body.extend(extracted_assignments)
            new_body.append(statement)
            changed = True
        else:
            new_body.append(statement)

    if not changed:
        return MutationResult(
            code=code,
            changed=False,
            summary="No safe config dictionary entries were found to spread.",
            edits=[],
            warnings=warnings,
        )

    tree.body = new_body
    ast.fix_missing_locations(tree)

    return MutationResult(
        code=ast.unparse(tree),
        changed=True,
        summary=f"Spread {len(edits)} config value(s) into separate constants.",
        edits=edits,
        warnings=warnings,
    )


def spread_configuration_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def spread_configuration(code: str) -> str:
    """Spread safe Python config dictionary values into separate constants."""
    result = mutate_source(code)
    return result.code
