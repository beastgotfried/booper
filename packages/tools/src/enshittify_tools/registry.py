"""Registry primitives for harness-callable tools."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from enshittify_tools.catalog import MUTATION_TOOL_SPECS, ToolSpec


class ToolRegistry:
    def __init__(self, specs: Iterable[ToolSpec] = MUTATION_TOOL_SPECS) -> None:
        self._specs = {spec.name: spec for spec in specs}

    def names(self) -> list[str]:
        return list(self._specs)

    def specs(self) -> list[ToolSpec]:
        return list(self._specs.values())

    def get_spec(self, name: str) -> ToolSpec:
        try:
            return self._specs[name]
        except KeyError as error:
            raise KeyError(f"Unknown tool: {name}") from error

    def get_tool(self, name: str) -> Any:
        return self.get_spec(name).tool

    def select_tools(self, names: Iterable[str]) -> list[Any]:
        return [self.get_tool(name) for name in names]


def create_default_registry() -> ToolRegistry:
    return ToolRegistry()
