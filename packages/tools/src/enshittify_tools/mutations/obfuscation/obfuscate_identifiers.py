"""LangChain tool for obfuscating Python identifiers."""

from __future__ import annotations

import ast
import builtins
import keyword

from langchain.tools import tool

from enshittify_tools.result import MutationEdit, MutationResult

_RESERVED_NAMES = {
    *dir(builtins),
    *keyword.kwlist,
    "self",
    "cls",
}


def _should_rename(name: str, blocked_names: set[str]) -> bool:
    if name in blocked_names:
        return False
    if not name.isidentifier() or keyword.iskeyword(name):
        return False
    return not (name.startswith("__") and name.endswith("__"))


def _make_obfuscated_name(index: int, blocked_names: set[str]) -> str:
    alphabet = "lI10O"
    current = index

    while True:
        chars: list[str] = []

        while True:
            chars.append(alphabet[current % len(alphabet)])
            current //= len(alphabet)
            if current == 0:
                break

        candidate = "_" + "".join(chars)
        if candidate not in blocked_names:
            return candidate

        index += 1
        current = index


class _ImportCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".", maxsplit=1)[0]
            self.names.add(local_name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                continue
            local_name = alias.asname or alias.name
            self.names.add(local_name)


class _RenameCandidateCollector(ast.NodeVisitor):
    def __init__(self, blocked_names: set[str]) -> None:
        self.blocked_names = blocked_names
        self.candidates: list[str] = []
        self.candidate_lines: dict[str, int | None] = {}
        self.all_names: set[str] = set()
        self._seen_candidates: set[str] = set()

    def _add_candidate(self, name: str, line: int | None) -> None:
        self.all_names.add(name)

        if name in self._seen_candidates:
            return
        if not _should_rename(name, self.blocked_names):
            return

        self.candidates.append(name)
        self.candidate_lines[name] = line
        self._seen_candidates.add(name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.all_names.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.all_names.add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.all_names.add(node.name)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        self._add_candidate(node.arg, getattr(node, "lineno", None))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        self.all_names.add(node.id)

        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self._add_candidate(node.id, getattr(node, "lineno", None))

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name is not None:
            self._add_candidate(node.name, getattr(node, "lineno", None))
        self.generic_visit(node)


class _IdentifierRenamer(ast.NodeTransformer):
    def __init__(self, rename_map: dict[str, str]) -> None:
        self.rename_map = rename_map

    def visit_arg(self, node: ast.arg) -> ast.arg:
        if node.arg in self.rename_map:
            node.arg = self.rename_map[node.arg]
        return node

    def visit_Name(self, node: ast.Name) -> ast.Name:
        if node.id in self.rename_map:
            node.id = self.rename_map[node.id]
        return node

    def visit_Global(self, node: ast.Global) -> ast.Global:
        node.names = [self.rename_map.get(name, name) for name in node.names]
        return node

    def visit_Nonlocal(self, node: ast.Nonlocal) -> ast.Nonlocal:
        node.names = [self.rename_map.get(name, name) for name in node.names]
        return node

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> ast.ExceptHandler:
        if node.name is not None:
            node.name = self.rename_map.get(node.name, node.name)
        self.generic_visit(node)
        return node


def mutate_source(code: str) -> MutationResult:
    """Return Python source code with local identifiers renamed."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return MutationResult(
            code=code,
            changed=False,
            summary="No identifiers were obfuscated because the source could not be parsed.",
            edits=[],
            warnings=[f"SyntaxError on line {error.lineno}: {error.msg}"],
        )

    import_collector = _ImportCollector()
    import_collector.visit(tree)

    blocked_names = _RESERVED_NAMES | import_collector.names
    candidate_collector = _RenameCandidateCollector(blocked_names)
    candidate_collector.visit(tree)

    used_names = blocked_names | candidate_collector.all_names
    rename_map: dict[str, str] = {}

    for original_name in candidate_collector.candidates:
        replacement = _make_obfuscated_name(len(rename_map), used_names)
        rename_map[original_name] = replacement
        used_names.add(replacement)

    if not rename_map:
        return MutationResult(
            code=code,
            changed=False,
            summary="No safe identifier rename candidates were found.",
            edits=[],
            warnings=[],
        )

    renamed_tree = _IdentifierRenamer(rename_map).visit(tree)
    ast.fix_missing_locations(renamed_tree)

    edits = [
        MutationEdit(
            kind="rename_identifier",
            before=original_name,
            after=replacement,
            line=candidate_collector.candidate_lines.get(original_name),
        )
        for original_name, replacement in rename_map.items()
    ]

    return MutationResult(
        code=ast.unparse(renamed_tree),
        changed=True,
        summary=f"Renamed {len(rename_map)} identifier(s).",
        edits=edits,
        warnings=[],
    )


def obfuscate_identifier_source(code: str) -> MutationResult:
    """Compatibility helper for graph nodes that need structured output."""
    return mutate_source(code)


@tool
def obfuscate_identifiers(code: str) -> str:
    """Rename Python variables and arguments to unreadable identifiers."""
    result = mutate_source(code)
    return result.code
