"""Model-loop convenience helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from enshittify_core.harness.create_harness import create_harness


def run_harness(code: str, tool_names: Iterable[str]) -> dict[str, Any]:
    graph = create_harness()
    return graph.invoke({"code": code, "tool_names": list(tool_names)})
