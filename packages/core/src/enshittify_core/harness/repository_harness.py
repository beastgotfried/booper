"""Repository-level mutation harness and artifact reporting."""

from __future__ import annotations

import difflib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from enshittify_backends import PreparedWorkspace
from enshittify_backends.artifacts import archive_directory, write_json, write_text
from enshittify_languages import inspect_repository, iter_python_files
from enshittify_profiles import get_profile
from enshittify_providers import CodxProvider, ModelProvider
from enshittify_tools.catalog import list_mutation_tool_names

from enshittify_core.harness.execution import (
    run_agent_execution,
    run_deterministic_execution,
)

HARNESS_MODES = frozenset({"agent", "deterministic", "hybrid"})
OUTPUT_MODES = frozenset({"archive", "patch", "workspace"})


@dataclass(frozen=True)
class RepositoryRunResult:
    run_id: str
    status: str
    run_dir: Path
    workspace_dir: Path
    report_path: Path
    patch_path: Path
    archive_path: Path | None
    report: dict[str, Any]

    @property
    def changed_files(self) -> list[str]:
        return list(self.report["summary"]["changed_files"])

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.report,
            "artifacts": {
                **self.report["artifacts"],
                "run_dir": str(self.run_dir),
                "workspace": str(self.workspace_dir),
                "report": str(self.report_path),
                "patch": str(self.patch_path),
                "archive": str(self.archive_path) if self.archive_path else None,
            },
        }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _generate_patch(
    original_root: Path,
    working_root: Path,
    changed_files: Iterable[str],
) -> str:
    chunks: list[str] = []
    for relative_path in sorted(changed_files):
        original = (original_root / relative_path).read_text(encoding="utf-8")
        mutated = (working_root / relative_path).read_text(encoding="utf-8")
        chunks.extend(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                mutated.splitlines(keepends=True),
                fromfile=f"a/{relative_path}",
                tofile=f"b/{relative_path}",
            )
        )
    return "".join(chunks)


def _score_run(
    *,
    candidate_count: int,
    changed_files: list[str],
    attempted_invocations: int,
    changed_invocations: int,
    lines_before: int,
    lines_after: int,
) -> float:
    file_ratio = len(changed_files) / candidate_count if candidate_count else 0.0
    tool_ratio = (
        changed_invocations / attempted_invocations if attempted_invocations else 0.0
    )
    line_growth = max(0.0, (lines_after - lines_before) / max(lines_before, 1))
    score = (file_ratio * 35.0) + (tool_ratio * 50.0) + (min(line_growth, 1.0) * 15.0)
    return round(min(score, 100.0), 2)


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    artifacts = report["artifacts"]
    lines = [
        f"# enshittify.dev run {report['run_id']}",
        "",
        f"- Status: `{report['status']}`",
        f"- Source: `{report['source']['display']}`",
        f"- Profile: `{report['configuration']['profile']}`",
        f"- Intensity: `{report['configuration']['intensity']}`",
        f"- Mode: `{report['configuration']['mode']}`",
        f"- Badness score: `{summary['badness_score']}` / `100`",
        f"- Files changed: `{len(summary['changed_files'])}` / `{summary['candidate_files']}`",
        f"- Tool invocations: `{summary['attempted_tool_invocations']}`",
        "",
        "## Artifacts",
        "",
        f"- Mutated workspace: `{artifacts['workspace']}`",
        f"- Unified patch: `{artifacts['patch']}`",
        f"- Machine report: `{artifacts['report_json']}`",
    ]
    if artifacts.get("archive"):
        lines.append(f"- Workspace archive: `{artifacts['archive']}`")
    if artifacts.get("codx_session"):
        lines.extend(
            [
                f"- Codx MCP session: `{artifacts['codx_session']}`",
                f"- Codx action state: `{artifacts['codx_state']}`",
                f"- Codx final message: `{artifacts['codx_last_message']}`",
            ]
        )

    if report["agent"]:
        agent = report["agent"]
        usage = agent["usage"]
        lines.extend(
            [
                "",
                "## Model Harness",
                "",
                f"- Provider: `{agent['provider']['name']}`",
                f"- Model: `{agent['provider']['model']}`",
                f"- Model calls: `{agent['model_calls']}`",
                f"- Tokens: `{usage['total_tokens']}`",
                f"- Stop reason: `{agent['stopped_reason']}`",
                f"- Deterministic fallback: `{agent['fallback_used']}`",
            ]
        )
        if agent["actions"]:
            lines.extend(["", "### Agent Actions", ""])
            lines.extend(
                f"- `{action['sequence']}` `{action['actor']}` `{action['tool']}` "
                f"on `{action['path']}`: {action['status']}"
                for action in agent["actions"]
            )

    lines.extend(["", "## Changed Files", ""])
    if summary["changed_files"]:
        lines.extend(f"- `{path}`" for path in summary["changed_files"])
    else:
        lines.append("No files changed.")

    lines.extend(["", "## Tool Activity", ""])
    for name, activity in report["tool_activity"].items():
        lines.append(
            f"- `{name}`: {activity['changed']} changed / "
            f"{activity['invocations']} invocation(s), {activity['planned']} planned, "
            f"{activity['edits']} edit(s)"
        )

    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    return "\n".join(lines) + "\n"


class RepositoryHarness:
    """Apply deterministic or model-directed mutations to a staged repository."""

    def run(
        self,
        workspace: PreparedWorkspace,
        *,
        profile_name: str = "maximum",
        intensity: str = "high",
        budget: int | None = None,
        include_tests: bool = False,
        dry_run: bool = False,
        tools: Iterable[str] | None = None,
        output: str = "workspace",
        max_file_bytes: int = 1_000_000,
        provider: ModelProvider | CodxProvider | None = None,
        mode: str = "deterministic",
        allow_llm_rewrites: bool = True,
        max_agent_steps: int = 24,
        max_agent_read_chars: int = 24_000,
        instruction: str | None = None,
    ) -> RepositoryRunResult:
        if budget is not None and budget < 1:
            raise ValueError("Budget must be at least 1 when provided.")
        if output not in OUTPUT_MODES:
            choices = ", ".join(sorted(OUTPUT_MODES))
            raise ValueError(f"Unknown output mode `{output}`. Choose from: {choices}.")
        if mode not in HARNESS_MODES:
            choices = ", ".join(sorted(HARNESS_MODES))
            raise ValueError(f"Unknown harness mode `{mode}`. Choose from: {choices}.")
        if mode != "deterministic" and provider is None:
            raise ValueError(f"Harness mode `{mode}` requires an LLM provider.")
        if max_agent_steps < 1:
            raise ValueError("max_agent_steps must be at least 1.")
        if max_agent_read_chars < 1:
            raise ValueError("max_agent_read_chars must be at least 1.")

        started_at = _utc_now()
        profile = get_profile(profile_name)
        selected_tools = (
            list(tools) if tools is not None else profile.select_tools(intensity)
        )
        known_tools = set(list_mutation_tool_names())
        unknown_tools = sorted(set(selected_tools) - known_tools)
        if unknown_tools:
            raise ValueError(f"Unknown mutation tool(s): {', '.join(unknown_tools)}")
        if not selected_tools:
            raise ValueError("At least one mutation tool must be selected.")

        inspection = inspect_repository(
            workspace.working_dir,
            max_file_bytes=max_file_bytes,
        )
        candidate_paths = iter_python_files(
            workspace.working_dir,
            include_tests=include_tests,
            max_file_bytes=max_file_bytes,
        )

        if mode == "deterministic":
            execution = run_deterministic_execution(
                workspace_root=workspace.working_dir,
                candidate_paths=candidate_paths,
                selected_tools=selected_tools,
                budget=budget,
                dry_run=dry_run,
            )
        else:
            assert provider is not None
            execution = run_agent_execution(
                workspace_root=workspace.working_dir,
                original_root=workspace.original_dir,
                candidate_paths=candidate_paths,
                inspection=inspection,
                selected_tools=selected_tools,
                profile=profile.name,
                intensity=intensity,
                budget=budget,
                dry_run=dry_run,
                provider=provider,
                mode=mode,
                allow_rewrites=allow_llm_rewrites,
                max_agent_steps=max_agent_steps,
                max_read_chars=max_agent_read_chars,
                instruction=instruction,
                artifact_root=workspace.artifacts_dir,
            )

        events: list[dict[str, Any]] = [
            {
                "at": started_at,
                "type": "run_started",
                "run_id": workspace.run_id,
                "profile": profile.name,
                "mode": mode,
                "tools": selected_tools,
            },
            *execution.events,
        ]
        warnings = list(execution.warnings)
        if not candidate_paths:
            warnings = list(
                dict.fromkeys(
                    [
                        "No eligible Python files were found in the repository.",
                        *warnings,
                    ]
                )
            )
        file_results = execution.file_results
        changed_files = execution.changed_files
        planned_invocations = execution.planned_invocations
        attempted_invocations = execution.attempted_invocations
        changed_invocations = execution.changed_invocations
        lines_before = execution.lines_before
        lines_after = execution.lines_after
        tool_activity = execution.tool_activity

        patch_content = _generate_patch(
            workspace.original_dir,
            workspace.working_dir,
            changed_files,
        )
        patch_path = write_text(workspace.artifacts_dir / "patch.diff", patch_content)
        archive_path = None
        if output == "archive" and not dry_run:
            archive_path = archive_directory(
                workspace.working_dir,
                workspace.artifacts_dir / "mutated-workspace",
            )

        status = "dry_run" if dry_run else "completed"
        if (
            execution.agent
            and mode == "agent"
            and execution.agent.stopped_reason == "provider_error"
            and not changed_files
        ):
            status = "failed"
        if warnings and status == "completed":
            status = "completed_with_warnings"
        badness_score = _score_run(
            candidate_count=len(candidate_paths),
            changed_files=changed_files,
            attempted_invocations=attempted_invocations,
            changed_invocations=changed_invocations,
            lines_before=lines_before,
            lines_after=lines_after,
        )
        completed_at = _utc_now()
        report_json_path = workspace.artifacts_dir / "report.json"
        report_markdown_path = workspace.artifacts_dir / "report.md"
        events_path = workspace.artifacts_dir / "events.jsonl"
        manifest_path = workspace.artifacts_dir / "manifest.json"
        artifact_paths: dict[str, str | None] = {
            "workspace": str(workspace.working_dir),
            "patch": str(patch_path),
            "report_json": str(report_json_path),
            "report_markdown": str(report_markdown_path),
            "events": str(events_path),
            "manifest": str(manifest_path),
            "archive": str(archive_path) if archive_path else None,
        }
        if isinstance(provider, CodxProvider):
            artifact_paths.update(
                {
                    "codx_session": str(workspace.artifacts_dir / "codx-session.json"),
                    "codx_state": str(
                        workspace.artifacts_dir / "codx-session-state.json"
                    ),
                    "codx_last_message": str(
                        workspace.artifacts_dir / "codx-last-message.txt"
                    ),
                }
            )
        events.append(
            {
                "at": completed_at,
                "type": "run_completed",
                "status": status,
                "changed_files": len(changed_files),
                "badness_score": badness_score,
            }
        )

        report: dict[str, Any] = {
            "schema_version": 2,
            "run_id": workspace.run_id,
            "status": status,
            "started_at": started_at,
            "completed_at": completed_at,
            "source": {
                "display": workspace.source,
                "kind": workspace.source_kind,
                "revision": workspace.revision,
            },
            "configuration": {
                "profile": profile.name,
                "intensity": intensity,
                "mode": mode,
                "provider": (
                    execution.agent.provider.model_dump(mode="json")
                    if execution.agent
                    else {"name": "none", "model": None, "capabilities": []}
                ),
                "budget": budget,
                "effective_budget": execution.effective_budget,
                "include_tests": include_tests,
                "dry_run": dry_run,
                "output": output,
                "tools": selected_tools,
                "allow_llm_rewrites": allow_llm_rewrites,
                "max_agent_steps": max_agent_steps,
                "max_agent_read_chars": max_agent_read_chars,
            },
            "inspection": inspection.to_dict(),
            "summary": {
                "candidate_files": len(candidate_paths),
                "processed_files": len(file_results),
                "changed_files": changed_files,
                "attempted_tool_invocations": attempted_invocations,
                "planned_tool_invocations": planned_invocations,
                "changed_tool_invocations": changed_invocations,
                "lines_before": lines_before,
                "lines_after": lines_after,
                "badness_score": badness_score,
            },
            "tool_activity": tool_activity,
            "files": file_results,
            "agent": (
                execution.agent.model_dump(mode="json") if execution.agent else None
            ),
            "warnings": warnings,
            "artifacts": artifact_paths,
        }

        manifest = {
            "schema_version": 2,
            "run_id": workspace.run_id,
            "source": report["source"],
            "configuration": report["configuration"],
            "changed_files": changed_files,
            "file_hashes": [
                {
                    "path": result["path"],
                    "before_sha256": result.get("before_sha256"),
                    "after_sha256": result.get("after_sha256"),
                }
                for result in file_results
            ],
        }
        write_text(
            events_path,
            "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        )
        write_json(manifest_path, manifest)
        write_json(report_json_path, report)
        write_text(report_markdown_path, _render_markdown(report))

        return RepositoryRunResult(
            run_id=workspace.run_id,
            status=status,
            run_dir=workspace.run_dir,
            workspace_dir=workspace.working_dir,
            report_path=report_json_path,
            patch_path=patch_path,
            archive_path=archive_path,
            report=report,
        )
