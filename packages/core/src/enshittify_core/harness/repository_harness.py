"""Repository-level mutation harness and artifact reporting."""

from __future__ import annotations

import difflib
import hashlib
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
from enshittify_tools.catalog import list_mutation_tool_names
from enshittify_tools.result import ToolChainResult

from enshittify_core.harness.create_harness import create_harness

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


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _line_count(content: str) -> int:
    return len(content.splitlines())


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

    lines.extend(["", "## Changed Files", ""])
    if summary["changed_files"]:
        lines.extend(f"- `{path}`" for path in summary["changed_files"])
    else:
        lines.append("No files changed.")

    lines.extend(["", "## Tool Activity", ""])
    for name, activity in report["tool_activity"].items():
        lines.append(
            f"- `{name}`: {activity['changed']} changed / "
            f"{activity['invocations']} invocation(s), {activity['edits']} edit(s)"
        )

    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    return "\n".join(lines) + "\n"


class RepositoryHarness:
    """Apply a deterministic LangGraph mutation harness across a staged repository."""

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
    ) -> RepositoryRunResult:
        if budget is not None and budget < 1:
            raise ValueError("Budget must be at least 1 when provided.")
        if output not in OUTPUT_MODES:
            choices = ", ".join(sorted(OUTPUT_MODES))
            raise ValueError(f"Unknown output mode `{output}`. Choose from: {choices}.")

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

        events: list[dict[str, Any]] = []
        warnings: list[str] = []
        file_results: list[dict[str, Any]] = []
        changed_files: list[str] = []
        planned_invocations = 0
        attempted_invocations = 0
        changed_invocations = 0
        lines_before = 0
        lines_after = 0
        tool_activity = {
            name: {"invocations": 0, "changed": 0, "edits": 0}
            for name in selected_tools
        }

        def emit(event_type: str, **payload: Any) -> None:
            events.append({"at": _utc_now(), "type": event_type, **payload})

        emit(
            "run_started",
            run_id=workspace.run_id,
            profile=profile.name,
            tools=selected_tools,
        )
        if not candidate_paths:
            warnings.append("No eligible Python files were found in the repository.")

        graph = create_harness() if candidate_paths and not dry_run else None
        for path in candidate_paths:
            if budget is not None and planned_invocations >= budget:
                emit("budget_exhausted", budget=budget)
                break

            relative_path = path.relative_to(workspace.working_dir).as_posix()
            try:
                original_code = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                warning = f"Skipped `{relative_path}`: {error}"
                warnings.append(warning)
                emit("file_skipped", path=relative_path, reason=str(error))
                continue

            lines_before += _line_count(original_code)
            names_for_file = selected_tools
            if budget is not None:
                remaining = budget - planned_invocations
                names_for_file = selected_tools[:remaining]
            planned_invocations += len(names_for_file)

            emit("file_started", path=relative_path, tools=names_for_file)
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
                emit("file_planned", path=relative_path)
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
            except Exception as error:  # noqa: BLE001 - one bad file must not abort a run
                warning = (
                    f"Mutation failed for `{relative_path}`: "
                    f"{type(error).__name__}: {error}"
                )
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
                emit("file_failed", path=relative_path, error=str(error))
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
            emit("file_completed", path=relative_path, changed=chain.changed)

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
        emit(
            "run_completed",
            status=status,
            changed_files=len(changed_files),
            badness_score=badness_score,
        )

        report: dict[str, Any] = {
            "schema_version": 1,
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
                "budget": budget,
                "include_tests": include_tests,
                "dry_run": dry_run,
                "output": output,
                "tools": selected_tools,
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
            "warnings": warnings,
            "artifacts": {
                "workspace": str(workspace.working_dir),
                "patch": str(patch_path),
                "report_json": str(report_json_path),
                "report_markdown": str(report_markdown_path),
                "events": str(events_path),
                "manifest": str(manifest_path),
                "archive": str(archive_path) if archive_path else None,
            },
        }

        manifest = {
            "schema_version": 1,
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
