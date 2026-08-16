"""Harness wrapper around the compiled mutation graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class MutationHarness:
    graph: Any

    def invoke(self, code: str, tool_names: Iterable[str]) -> dict[str, Any]:
        return self.graph.invoke({"code": code, "tool_names": list(tool_names)})
