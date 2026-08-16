"""Minimal MCP stdio server exposing one isolated enshittify session.

The server intentionally implements only the MCP methods required by the Codex
CLI. It keeps the model-facing boundary separate from the mutation engine and
never writes to stdout except for JSON-RPC frames.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from enshittify_tools.agent.session import AgentWorkspaceSession

_SERVER_NAME = "enshittify"
_SERVER_VERSION = "0.1.0"
_DEFAULT_PROTOCOL_VERSION = "2024-11-05"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _tool_annotations(*, read_only: bool) -> dict[str, bool]:
    return {
        "readOnlyHint": read_only,
        "destructiveHint": not read_only,
        "idempotentHint": read_only,
        "openWorldHint": False,
    }


def _tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "inspect_workspace",
            "description": (
                "Inspect eligible files, repository metadata, mutation names, and the "
                "remaining action budget."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "annotations": _tool_annotations(read_only=True),
        },
        {
            "name": "read_source",
            "description": "Read one exact eligible Python source path.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Exact relative path returned by inspect_workspace.",
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            "annotations": _tool_annotations(read_only=True),
        },
        {
            "name": "apply_mutation",
            "description": (
                "Apply one allowlisted deterministic mutation to one eligible Python file. "
                "The mutation name must come from inspect_workspace."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "mutation": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["path", "mutation"],
                "additionalProperties": False,
            },
            "annotations": _tool_annotations(read_only=False),
        },
        {
            "name": "rewrite_source",
            "description": (
                "Replace one eligible Python file with a bounded, syntax-validated source "
                "rewrite. Return raw source without Markdown fences."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "code": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["path", "code", "rationale"],
                "additionalProperties": False,
            },
            "annotations": _tool_annotations(read_only=False),
        },
        {
            "name": "review_diff",
            "description": "Review the bounded diff for one path or all changed paths.",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": ["string", "null"]}},
                "additionalProperties": False,
            },
            "annotations": _tool_annotations(read_only=True),
        },
    ]


class StdioMcpSession:
    """Serve one configured workspace session over line-delimited JSON-RPC."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.session = AgentWorkspaceSession(
            workspace_root=Path(config["workspace_root"]),
            original_root=Path(config["original_root"]),
            candidate_paths=[
                Path(config["workspace_root"]) / relative
                for relative in config.get("candidate_paths", [])
            ],
            inspection=dict(config.get("inspection", {})),
            allowed_mutations=tuple(config.get("allowed_mutations", [])),
            mutation_descriptions=dict(config.get("mutation_descriptions", {})),
            profile=str(config.get("profile", "maximum")),
            intensity=str(config.get("intensity", "high")),
            budget=int(config["budget"]),
            dry_run=bool(config.get("dry_run", False)),
            allow_rewrites=bool(config.get("allow_rewrites", True)),
            max_read_chars=int(config.get("max_read_chars", 24_000)),
            max_rewrite_chars=int(config.get("max_rewrite_chars", 100_000)),
            max_diff_chars=int(config.get("max_diff_chars", 32_000)),
        )
        state_path = config.get("state_path")
        self.state_path = Path(state_path) if state_path else None
        self.save_state()

    def save_state(self) -> None:
        if self.state_path is None:
            return
        payload = {
            "actions": [
                action.model_dump(mode="json") for action in self.session.actions
            ],
            "changed_paths": self.session.changed_paths(),
            "warnings": list(self.session.warnings),
            "used_budget": self.session.used_budget,
            "remaining_budget": self.session.remaining_budget,
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(_json(payload) + "\n", encoding="utf-8")

    def call(self, name: str, arguments: dict[str, Any]) -> tuple[str, bool]:
        if name == "inspect_workspace":
            result = self.session.inspect_workspace()
        elif name == "read_source":
            result = self.session.read_source(str(arguments.get("path", "")))
        elif name == "apply_mutation":
            result = self.session.apply_mutation(
                str(arguments.get("path", "")),
                str(arguments.get("mutation", "")),
                str(arguments.get("rationale", "")),
            )
        elif name == "rewrite_source":
            result = self.session.rewrite_source(
                str(arguments.get("path", "")),
                str(arguments.get("code", "")),
                str(arguments.get("rationale", "")),
            )
        elif name == "review_diff":
            path = arguments.get("path")
            result = self.session.review_diff(str(path) if path is not None else None)
        else:
            return _json(
                {"ok": False, "error": f"Unknown enshittify tool: {name}"}
            ), True

        self.save_state()
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            return result, False
        return result, not bool(parsed.get("ok", True))

    def serve(self) -> None:
        for raw_line in sys.stdin:
            if not raw_line.strip():
                continue
            request: dict[str, Any] | None = None
            try:
                request = json.loads(raw_line)
                response = self.handle(request)
            except Exception as error:  # noqa: BLE001 - JSON-RPC boundary must stay alive
                request_id = request.get("id") if isinstance(request, dict) else None
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"enshittify MCP server error: {type(error).__name__}: {error}",
                    },
                }
                print(response["error"]["message"], file=sys.stderr)
            if response is not None:
                sys.stdout.write(_json(response) + "\n")
                sys.stdout.flush()
        self.save_state()

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        if method in {
            "notifications/initialized",
            "notifications/cancelled",
            "notifications/progress",
        }:
            return None
        if method == "initialize":
            requested = request.get("params", {}).get("protocolVersion")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": requested or _DEFAULT_PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": _SERVER_NAME, "version": _SERVER_VERSION},
                },
            }
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": _tool_definitions()},
            }
        if method == "tools/call":
            params = request.get("params", {})
            result, is_error = self.call(
                str(params.get("name", "")),
                dict(params.get("arguments") or {}),
            )
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": result}],
                    "isError": is_error,
                },
            }
        if request_id is None:
            return None
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve an enshittify session over MCP stdio."
    )
    parser.add_argument("--config", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    StdioMcpSession(config).serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
