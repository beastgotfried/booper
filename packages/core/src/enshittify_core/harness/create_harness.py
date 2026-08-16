"""Factory for compiled harness graphs."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from enshittify_core.runtime.tool_dispatch import run_tool_chain
from enshittify_core.state.session import HarnessState


def _apply_mutation_tools(state: HarnessState) -> dict[str, object]:
    result = run_tool_chain(state["tool_names"], state["code"])
    return {
        "code": result.code,
        "result": result,
        "warnings": result.warnings,
    }


def create_harness():
    graph = StateGraph(HarnessState)
    graph.add_node("apply_mutation_tools", _apply_mutation_tools)
    graph.add_edge(START, "apply_mutation_tools")
    graph.add_edge("apply_mutation_tools", END)
    return graph.compile()
