"""Run the harness through the authorized local ``codx`` CLI wrapper."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from enshittify_protocol import AgentAction, AgentRunSummary, ModelUsage
from enshittify_providers import CodxProvider
from enshittify_providers.normalize import redact_provider_text
from enshittify_tools.agent import AgentWorkspaceSession

from enshittify_core.context.prompt import (
    build_agent_system_prompt,
    build_agent_task_prompt,
)


def run_codx_harness(
    session: AgentWorkspaceSession,
    provider: CodxProvider,
    *,
    mode: str,
    max_agent_steps: int,
    instruction: str | None,
    artifact_root: Path,
) -> AgentRunSummary:
    """Run Codx as the outer agent while enshittify owns all mutations."""
    artifact_root.mkdir(parents=True, exist_ok=True)
    config_path = artifact_root / "codx-session.json"
    state_path = artifact_root / "codx-session-state.json"
    last_message_path = artifact_root / "codx-last-message.txt"
    config_path.write_text(
        json.dumps(
            {
                "workspace_root": str(session.workspace_root),
                "original_root": str(session.original_root),
                "candidate_paths": list(session.candidate_names),
                "inspection": session.inspection,
                "allowed_mutations": list(session.allowed_mutations),
                "mutation_descriptions": session.mutation_descriptions,
                "profile": session.profile,
                "intensity": session.intensity,
                "budget": session.budget,
                "dry_run": session.dry_run,
                "allow_rewrites": session.allow_rewrites,
                "max_read_chars": session.max_read_chars,
                "max_rewrite_chars": session.max_rewrite_chars,
                "max_diff_chars": session.max_diff_chars,
                "state_path": str(state_path),
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    prompt = _build_codx_prompt(
        session,
        max_agent_steps=max_agent_steps,
        instruction=instruction,
    )
    command = _build_command(
        provider,
        workspace_root=session.workspace_root,
        config_path=config_path,
        last_message_path=last_message_path,
    )
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    stdout = ""
    stderr = ""
    stopped_reason = "completed"
    warnings: list[str] = []
    try:
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            cwd=session.workspace_root,
            env=environment,
            timeout=provider.timeout,
            check=False,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        if completed.returncode != 0:
            stopped_reason = "provider_error"
            warnings.append(f"Codx exited with status {completed.returncode}.")
    except subprocess.TimeoutExpired as error:
        stopped_reason = "timeout"
        stdout = _text_output(error.stdout)
        stderr = _text_output(error.stderr)
        warnings.append(f"Codx exceeded its {provider.timeout:g}-second timeout.")
    except OSError as error:
        stopped_reason = "provider_error"
        warnings.append(f"Could not launch Codx: {type(error).__name__}: {error}")

    event_data = _parse_events(stdout)
    warnings.extend(event_data["warnings"])
    if event_data["failed"] and stopped_reason == "completed":
        stopped_reason = "provider_error"
    warnings.extend(_stderr_warnings(stderr))

    actions, state_warnings = _read_state(state_path)
    warnings.extend(state_warnings)
    final_message = event_data["final_message"]
    if not final_message and last_message_path.is_file():
        try:
            final_message = last_message_path.read_text(encoding="utf-8").strip()
        except OSError:
            pass

    return AgentRunSummary(
        mode=mode,
        provider=provider.descriptor(),
        model_calls=event_data["model_calls"],
        usage=event_data["usage"],
        final_message=final_message,
        stopped_reason=stopped_reason,
        actions=tuple(actions),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def _build_codx_prompt(
    session: AgentWorkspaceSession,
    *,
    max_agent_steps: int,
    instruction: str | None,
) -> str:
    system = build_agent_system_prompt(
        profile=session.profile,
        intensity=session.intensity,
        budget=session.budget,
        candidate_paths=session.candidate_names,
        allow_rewrites=session.allow_rewrites,
        user_instruction=instruction,
    )
    return (
        f"{system}\n\n"
        "You are running inside Codex through the enshittify MCP server. The MCP server is "
        "the only authority allowed to inspect or mutate the target. Use only the five "
        "enshittify MCP tools; do not use Codex shell, patch, git, or direct file-editing "
        "tools. Do not modify files directly.\n"
        f"The maximum planning loop is {max_agent_steps} steps. The mutation budget is "
        "enforced by the MCP server.\n\n"
        f"{build_agent_task_prompt(dry_run=session.dry_run)}"
    )


def _build_command(
    provider: CodxProvider,
    *,
    workspace_root: Path,
    config_path: Path,
    last_message_path: Path,
) -> list[str]:
    mcp_args = [
        "-m",
        "enshittify_tools.agent.mcp_server",
        "--config",
        str(config_path),
    ]
    command = [provider.command]
    if provider.yolo:
        command.append("--yolo")
    command.extend(
        [
            "-c",
            f"mcp_servers.enshittify.command={json.dumps(sys.executable)}",
            "-c",
            f"mcp_servers.enshittify.args={json.dumps(mcp_args)}",
            "-c",
            f"mcp_servers.enshittify.cwd={json.dumps(str(workspace_root))}",
            "exec",
            "--json",
            "--ephemeral",
            "--skip-git-repo-check",
            "-C",
            str(workspace_root),
            "-s",
            "read-only",
            "-o",
            str(last_message_path),
        ]
    )
    if provider.model != "codex-default":
        command.extend(["-m", provider.model])
    return command


def _parse_events(output: str) -> dict[str, Any]:
    model_calls = 0
    usage = ModelUsage()
    final_message = ""
    warnings: list[str] = []
    failed = False
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "turn.started":
            model_calls += 1
        elif event.get("type") == "turn.completed":
            raw_usage = event.get("usage") or {}
            if not isinstance(raw_usage, dict):
                raw_usage = {}
            input_tokens = _int_value(raw_usage.get("input_tokens"))
            output_tokens = _int_value(raw_usage.get("output_tokens"))
            usage = usage.plus(
                ModelUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                )
            )
        elif event.get("type") in {"error", "turn.failed"}:
            failed = True
            message = event.get("message") or event.get("error") or str(event)
            warnings.append(
                f"Codx reported an error: {redact_provider_text(str(message))}"
            )
        elif event.get("type") == "item.completed":
            item = event.get("item") or {}
            if not isinstance(item, dict):
                continue
            if item.get("type") == "agent_message" and isinstance(
                item.get("text"), str
            ):
                final_message = item["text"]
            if item.get("status") == "failed":
                failed = True
                error = item.get("error") or "Codx item failed."
                warnings.append(f"Codx item failed: {redact_provider_text(str(error))}")
    return {
        "model_calls": model_calls,
        "usage": usage,
        "final_message": final_message,
        "warnings": warnings,
        "failed": failed,
    }


def _read_state(path: Path) -> tuple[list[AgentAction], list[str]]:
    if not path.is_file():
        return [], ["Codx did not produce an enshittify session state file."]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        actions = [
            AgentAction.model_validate(item) for item in payload.get("actions", [])
        ]
        warnings = [str(item) for item in payload.get("warnings", [])]
        return actions, warnings
    except (OSError, AttributeError, ValueError, TypeError) as error:
        return [], [
            f"Could not read Codx session state: {type(error).__name__}: {error}"
        ]


def _stderr_warnings(stderr: str) -> list[str]:
    meaningful = []
    for line in stderr.splitlines():
        stripped = line.strip()
        if _is_normal_startup_line(stripped):
            continue
        meaningful.append(redact_provider_text(stripped))
    if not meaningful:
        return []
    return [f"Codx stderr: {line}" for line in meaningful[-8:]]


def _is_normal_startup_line(line: str) -> bool:
    """Ignore wrapper noise while retaining actual provider diagnostics."""
    if not line or "SECURITY NOTICE" in line or "Terminated:" in line:
        return True
    if line == "Reading prompt from stdin...":
        return True
    if line.startswith("█"):
        return True
    if line.startswith("|") and "DO NOT use fast mode" in line:
        return True
    return not any(character.isalnum() for character in line)


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _text_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
