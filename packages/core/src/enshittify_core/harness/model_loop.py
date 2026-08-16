"""LangGraph-backed deterministic and model-directed harness loops."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from enshittify_protocol import AgentRunSummary, ModelUsage
from enshittify_providers import ModelProvider
from enshittify_providers.normalize import redact_provider_text
from enshittify_tools.agent import AgentWorkspaceSession, build_workspace_tools
from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langgraph.errors import GraphRecursionError

from enshittify_core.context.prompt import (
    build_agent_system_prompt,
    build_agent_task_prompt,
)
from enshittify_core.harness.create_harness import create_harness


def run_harness(code: str, tool_names: Iterable[str]) -> dict[str, Any]:
    graph = create_harness()
    return graph.invoke({"code": code, "tool_names": list(tool_names)})


def run_model_harness(
    session: AgentWorkspaceSession,
    provider: ModelProvider,
    *,
    mode: str,
    max_agent_steps: int = 24,
    instruction: str | None = None,
) -> AgentRunSummary:
    """Run a tool-calling model against one isolated workspace session."""
    if mode not in {"agent", "hybrid"}:
        raise ValueError("Model harness mode must be `agent` or `hybrid`.")
    if max_agent_steps < 1:
        raise ValueError("max_agent_steps must be at least 1.")

    system_prompt = build_agent_system_prompt(
        profile=session.profile,
        intensity=session.intensity,
        budget=session.budget,
        candidate_paths=session.candidate_names,
        allow_rewrites=session.allow_rewrites,
        user_instruction=instruction,
    )
    agent = create_agent(
        model=provider.chat_model,
        tools=build_workspace_tools(session),
        system_prompt=system_prompt,
        name="enshittify_agent",
    )

    messages: list[Any] = []
    warnings: list[str] = []
    stopped_reason = "completed"
    try:
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": build_agent_task_prompt(dry_run=session.dry_run),
                    }
                ]
            },
            {"recursion_limit": (max_agent_steps * 2) + 2},
        )
        messages = list(result.get("messages", []))
    except GraphRecursionError:
        stopped_reason = "step_limit"
        warnings.append(
            f"Agent stopped after reaching the {max_agent_steps}-step model-loop limit."
        )
    except Exception as error:  # noqa: BLE001 - hybrid mode can recover deterministically
        stopped_reason = "provider_error"
        detail = redact_provider_text(f"{type(error).__name__}: {error}")
        warnings.append(f"Model harness stopped after a provider error: {detail}")

    model_calls, usage = _collect_usage(messages)
    return AgentRunSummary(
        mode=mode,
        provider=provider.descriptor(),
        model_calls=model_calls,
        usage=usage,
        final_message=_final_message(messages),
        stopped_reason=stopped_reason,
        actions=tuple(session.actions),
        warnings=(*session.warnings, *warnings),
    )


def _collect_usage(messages: list[Any]) -> tuple[int, ModelUsage]:
    calls = 0
    usage = ModelUsage()
    for message in messages:
        if not isinstance(message, AIMessage):
            continue
        calls += 1
        metadata = message.usage_metadata or {}
        response_usage = message.response_metadata.get("token_usage", {})
        input_tokens = int(
            metadata.get("input_tokens", response_usage.get("prompt_tokens", 0)) or 0
        )
        output_tokens = int(
            metadata.get("output_tokens", response_usage.get("completion_tokens", 0))
            or 0
        )
        total_tokens = int(
            metadata.get("total_tokens", response_usage.get("total_tokens", 0)) or 0
        )
        usage = usage.plus(
            ModelUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens or input_tokens + output_tokens,
            )
        )
    return calls, usage


def _final_message(messages: list[Any]) -> str:
    for message in reversed(messages):
        if not isinstance(message, AIMessage) or message.tool_calls:
            continue
        if isinstance(message.content, str):
            return message.content
        return str(message.content)
    return ""
