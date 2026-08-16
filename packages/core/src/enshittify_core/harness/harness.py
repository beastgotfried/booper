"""Harness wrapper around the compiled mutation graph."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MutationHarness:
    graph: Any

    def invoke(
        self,
        code: str,
        tool_names: Iterable[str],
        *,
        continue_on_error: bool = False,
    ) -> dict[str, Any]:
        return self.graph.invoke(
            {
                "code": code,
                "tool_names": list(tool_names),
                "continue_on_error": continue_on_error,
            }
        )
