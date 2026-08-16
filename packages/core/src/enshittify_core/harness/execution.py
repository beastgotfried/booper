"""Execution strategies shared by the repository harness."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from enshittify_languages import RepositoryInspection
from enshittify_protocol import AgentRunSummary, ModelUsage
from enshittify_providers import CodxProvider, ModelProvider
from enshittify_tools.agent import AgentWorkspaceSession
from enshittify_tools.catalog import iter_mutation_tool_specs
from enshittify_tools.result import ToolChainResult

from enshittify_core.harness.codx_loop import run_codx_harness
from enshittify_core.harness.create_harness import create_harness
from enshittify_core.harness.model_loop import run_model_harness


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _line_count(content: str) -> int:
    return len(content.splitlines())


def _event(event_type: str, **payload: Any) -> dict[str, Any]:
    return {"at": _utc_now(), "type": event_type, **payload}


def _activity(names: list[str]) -> dict[str, dict[str, int]]:
    return {
        name: {"planned": 0, "invocations": 0, "changed": 0, "edits": 0}
        for name in names
    }


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


@dataclass
class ExecutionResult:
    file_results: list[dict[str, Any]]
    changed_files: list[str]
    planned_invocations: int
    attempted_invocations: int
    changed_invocations: int
    lines_before: int
    lines_after: int
    tool_activity: dict[str, dict[str, int]]
    warnings: list[str]
    events: list[dict[str, Any]]
    effective_budget: int | None
    agent: AgentRunSummary | None = None


def run_deterministic_execution(
    *,
    workspace_root: Path,
    candidate_paths: list[Path],
    selected_tools: list[str],
    budget: int | None,
    dry_run: bool,
) -> ExecutionResult:
    """Apply the existing deterministic chain across eligible files."""
    warnings: list[str] = []
    events: list[dict[str, Any]] = []
    file_results: list[dict[str, Any]] = []
    changed_files: list[str] = []
    planned_invocations = 0
    attempted_invocations = 0
    changed_invocations = 0
    lines_before = 0
    lines_after = 0
    tool_activity = _activity(selected_tools)

    graph = create_harness() if candidate_paths and not dry_run else None
    for path in candidate_paths:
        if budget is not None and planned_invocations >= budget:
            events.append(_event("budget_exhausted", budget=budget))
            break

        relative_path = path.relative_to(workspace_root).as_posix()
        try:
            original_code = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            warning = f"Skipped `{relative_path}`: {error}"
            warnings.append(warning)
            events.append(_event("file_skipped", path=relative_path, reason=str(error)))
            continue

        lines_before += _line_count(original_code)
        names_for_file = selected_tools
        if budget is not None:
            remaining = budget - planned_invocations
            names_for_file = selected_tools[:remaining]
        planned_invocations += len(names_for_file)
        for name in names_for_file:
            tool_activity[name]["planned"] += 1

        events.append(_event("file_started", path=relative_path, tools=names_for_file))
        if dry_run:
            file_results.append(
                {
                    "path": relative_path,
                    "changed": False,
                    "planned_tools": names_for_file,
                    "runs": [],
                }
            )
            lines_after += _line_count(original_code)
            events.append(_event("file_planned", path=relative_path))
            continue

        attempted_invocations += len(names_for_file)
        try:
            assert graph is not None
            graph_result = graph.invoke(
                {
                    "code": original_code,
                    "tool_names": names_for_file,
                    "continue_on_error": True,
                }
            )
            chain: ToolChainResult = graph_result["result"]
        except Exception as error:  # noqa: BLE001 - one file must not abort the run
            warning = f"Mutation failed for `{relative_path}`: {type(error).__name__}: {error}"
            warnings.append(warning)
            file_results.append(
                {
                    "path": relative_path,
                    "changed": False,
                    "error": str(error),
                    "planned_tools": names_for_file,
                    "runs": [],
                }
            )
            lines_after += _line_count(original_code)
            events.append(_event("file_failed", path=relative_path, error=str(error)))
            continue

        final_code = chain.code
        if (
            chain.changed
            and original_code.endswith("\n")
            and not final_code.endswith("\n")
        ):
            final_code += "\n"
        if chain.changed:
            path.write_text(final_code, encoding="utf-8")
            changed_files.append(relative_path)

        run_records: list[dict[str, Any]] = []
        for tool_run in chain.runs:
            activity = tool_activity[tool_run.name]
            activity["invocations"] += 1
            activity["edits"] += len(tool_run.result.edits)
            if tool_run.result.changed:
                activity["changed"] += 1
                changed_invocations += 1
            warnings.extend(
                f"`{relative_path}` / `{tool_run.name}`: {warning}"
                for warning in tool_run.result.warnings
            )
            run_records.append(
                {
                    "name": tool_run.name,
                    "actor": "deterministic",
                    "changed": tool_run.result.changed,
                    "summary": tool_run.result.summary,
                    "edit_count": len(tool_run.result.edits),
                    "warnings": list(tool_run.result.warnings),
                }
            )

        lines_after += _line_count(final_code)
        file_results.append(
            {
                "path": relative_path,
                "changed": chain.changed,
                "before_sha256": _sha256(original_code),
                "after_sha256": _sha256(final_code),
                "lines_before": _line_count(original_code),
                "lines_after": _line_count(final_code),
                "runs": run_records,
            }
        )
        events.append(
            _event("file_completed", path=relative_path, changed=chain.changed)
        )

    return ExecutionResult(
        file_results=file_results,
        changed_files=changed_files,
        planned_invocations=planned_invocations,
        attempted_invocations=attempted_invocations,
        changed_invocations=changed_invocations,
        lines_before=lines_before,
        lines_after=lines_after,
        tool_activity=tool_activity,
        warnings=_dedupe(warnings),
        events=events,
        effective_budget=budget,
    )


def run_agent_execution(
    *,
    workspace_root: Path,
    original_root: Path,
    candidate_paths: list[Path],
    inspection: RepositoryInspection,
    selected_tools: list[str],
    profile: str,
    intensity: str,
    budget: int | None,
    dry_run: bool,
    provider: ModelProvider | CodxProvider,
    mode: str,
    allow_rewrites: bool,
    max_agent_steps: int,
    max_read_chars: int,
    instruction: str | None,
    artifact_root: Path,
) -> ExecutionResult:
    """Run the model tool loop and optional deterministic budget fill."""
    effective_budget = budget or _default_agent_budget(len(candidate_paths), intensity)
    descriptions = {spec.name: spec.description for spec in iter_mutation_tool_specs()}
    session = AgentWorkspaceSession(
        workspace_root=workspace_root,
        original_root=original_root,
        candidate_paths=candidate_paths,
        inspection=inspection.to_dict(),
        allowed_mutations=tuple(selected_tools),
        mutation_descriptions=descriptions,
        profile=profile,
        intensity=intensity,
        budget=effective_budget,
        dry_run=dry_run,
        allow_rewrites=allow_rewrites,
        max_read_chars=max_read_chars,
    )
    events = [
        _event(
            "agent_started",
            provider=provider.name,
            model=provider.model,
            mode=mode,
            budget=effective_budget,
        )
    ]

    if candidate_paths:
        if isinstance(provider, CodxProvider):
            agent = run_codx_harness(
                session,
                provider,
                mode=mode,
                max_agent_steps=max_agent_steps,
                instruction=instruction,
                artifact_root=artifact_root,
            )
            # Codx runs the MCP server in a child process. Import its ledger into
            # the parent session so hybrid fallback, reports, and changed-path
            # accounting see the same actions as the native LangChain loop.
            session.actions.extend(agent.actions)
        else:
            agent = run_model_harness(
                session,
                provider,
                mode=mode,
                max_agent_steps=max_agent_steps,
                instruction=instruction,
            )
    else:
        agent = AgentRunSummary(
            mode=mode,
            provider=provider.descriptor(),
            usage=ModelUsage(),
            stopped_reason="no_candidates",
            warnings=("No eligible Python files were found in the repository.",),
        )

    action_count_before_fallback = len(session.actions)
    if mode == "hybrid" and session.remaining_budget:
        _fill_remaining_budget(session, candidate_paths, selected_tools)
    fallback_used = len(session.actions) > action_count_before_fallback

    combined_warnings = _dedupe([*agent.warnings, *session.warnings])
    agent = agent.model_copy(
        update={
            "actions": tuple(session.actions),
            "fallback_used": fallback_used,
            "warnings": tuple(combined_warnings),
        }
    )
    events.extend(
        _event("agent_action", action=action.model_dump(mode="json"))
        for action in session.actions
    )
    events.append(
        _event(
            "agent_completed",
            stopped_reason=agent.stopped_reason,
            model_calls=agent.model_calls,
            fallback_used=fallback_used,
            actions=len(session.actions),
        )
    )

    tool_names = [*selected_tools]
    if any(action.tool == "llm_rewrite" for action in session.actions):
        tool_names.append("llm_rewrite")
    tool_activity = _activity(list(dict.fromkeys(tool_names)))
    for action in session.actions:
        activity = tool_activity.setdefault(
            action.tool,
            {"planned": 0, "invocations": 0, "changed": 0, "edits": 0},
        )
        activity["planned"] += 1
        if not dry_run:
            activity["invocations"] += 1
        if action.status == "changed":
            activity["changed"] += 1
        activity["edits"] += action.edit_count

    file_results, lines_before, lines_after = _agent_file_results(
        workspace_root=workspace_root,
        original_root=original_root,
        candidate_paths=candidate_paths,
        agent=agent,
    )
    changed_files = session.changed_paths()
    return ExecutionResult(
        file_results=file_results,
        changed_files=changed_files,
        planned_invocations=len(session.actions),
        attempted_invocations=0 if dry_run else len(session.actions),
        changed_invocations=sum(
            action.status == "changed" for action in session.actions
        ),
        lines_before=lines_before,
        lines_after=lines_after,
        tool_activity=tool_activity,
        warnings=combined_warnings,
        events=events,
        effective_budget=effective_budget,
        agent=agent,
    )


def _fill_remaining_budget(
    session: AgentWorkspaceSession,
    candidate_paths: list[Path],
    selected_tools: list[str],
) -> None:
    used_pairs = {(action.path, action.tool) for action in session.actions}
    for path in candidate_paths:
        relative = path.relative_to(session.workspace_root).as_posix()
        for name in selected_tools:
            if session.remaining_budget == 0:
                return
            if (relative, name) in used_pairs:
                continue
            session.apply_mutation(
                relative,
                name,
                "Hybrid fallback used remaining budget after model-directed actions.",
                actor="fallback",
            )


def _agent_file_results(
    *,
    workspace_root: Path,
    original_root: Path,
    candidate_paths: list[Path],
    agent: AgentRunSummary,
) -> tuple[list[dict[str, Any]], int, int]:
    results: list[dict[str, Any]] = []
    lines_before = 0
    lines_after = 0
    for path in candidate_paths:
        relative = path.relative_to(workspace_root).as_posix()
        before = (original_root / relative).read_text(encoding="utf-8")
        after = path.read_text(encoding="utf-8")
        path_actions = [action for action in agent.actions if action.path == relative]
        lines_before += _line_count(before)
        lines_after += _line_count(after)
        results.append(
            {
                "path": relative,
                "changed": before != after,
                "before_sha256": _sha256(before),
                "after_sha256": _sha256(after),
                "lines_before": _line_count(before),
                "lines_after": _line_count(after),
                "planned_tools": [action.tool for action in path_actions],
                "runs": [
                    {
                        "name": action.tool,
                        "actor": action.actor,
                        "changed": action.status == "changed",
                        "status": action.status,
                        "summary": action.summary,
                        "rationale": action.rationale,
                        "edit_count": action.edit_count,
                        "warnings": list(action.warnings),
                    }
                    for action in path_actions
                ],
            }
        )
    return results, lines_before, lines_after


def _default_agent_budget(candidate_count: int, intensity: str) -> int:
    multiplier = {"low": 2, "medium": 3, "high": 4, "maximum": 6}[intensity]
    return max(1, min(candidate_count * multiplier, 60))
