from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

from enshittify_core.harness.codx_loop import _build_command, _parse_events
from enshittify_core.harness.execution import run_agent_execution
from enshittify_languages import inspect_repository
from enshittify_providers import CodxProvider


class CodxLoopTests(unittest.TestCase):
    def test_event_parser_collects_turns_usage_and_final_message(self) -> None:
        output = "\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": "t"}),
                json.dumps({"type": "turn.started"}),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "Finished."},
                    }
                ),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {"input_tokens": 11, "output_tokens": 7},
                    }
                ),
            ]
        )

        parsed = _parse_events(output)

        self.assertEqual(parsed["model_calls"], 1)
        self.assertEqual(parsed["usage"].total_tokens, 18)
        self.assertEqual(parsed["final_message"], "Finished.")
        self.assertFalse(parsed["failed"])

    def test_event_parser_ignores_malformed_usage_and_non_object_events(self) -> None:
        parsed = _parse_events(
            "\n".join(
                [
                    "[]",
                    json.dumps(
                        {
                            "type": "turn.completed",
                            "usage": {"input_tokens": "not-a-number"},
                        }
                    ),
                ]
            )
        )

        self.assertEqual(parsed["model_calls"], 0)
        self.assertEqual(parsed["usage"].total_tokens, 0)

    def test_command_uses_non_interactive_exec_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = CodxProvider(command="codx", yolo=True)
            command = _build_command(
                provider,
                workspace_root=root,
                config_path=root / "session.json",
                last_message_path=root / "last-message.txt",
            )

        self.assertEqual(command[0:2], ["codx", "--yolo"])
        self.assertIn("exec", command)
        self.assertIn("--json", command)
        self.assertIn("--ephemeral", command)
        self.assertNotIn("--interactive", command)

    def test_parent_execution_adopts_actions_from_mcp_child(self) -> None:
        fake_codx = """#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

args_config = next(
    value for value in sys.argv
    if value.startswith("mcp_servers.enshittify.args=")
)
mcp_args = json.loads(args_config.split("=", 1)[1])
config_path = Path(mcp_args[mcp_args.index("--config") + 1])
config = json.loads(config_path.read_text())
server = subprocess.Popen(
    [sys.executable, "-m", "enshittify_tools.agent.mcp_server", "--config", str(config_path)],
    cwd=config["workspace_root"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
)

def call(request):
    server.stdin.write(json.dumps(request) + "\\n")
    server.stdin.flush()
    return json.loads(server.stdout.readline())

call({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}})
call({
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "apply_mutation",
        "arguments": {
            "path": config["candidate_paths"][0],
            "mutation": config["allowed_mutations"][0],
            "rationale": "Exercise the MCP action ledger.",
        },
    },
})
server.stdin.close()
server.wait()
print(json.dumps({"type": "turn.started"}))
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 3, "output_tokens": 2}}))
print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Used MCP."}}))
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original"
            workspace = root / "workspace"
            original.mkdir()
            workspace.mkdir()
            source = "def calculate_total(readable_value):\n    return readable_value\n"
            (original / "main.py").write_text(source, encoding="utf-8")
            (workspace / "main.py").write_text(source, encoding="utf-8")
            fake_path = root / "fake-codx"
            fake_path.write_text(
                f"#!{sys.executable}\n{fake_codx.split(chr(10), 1)[1]}",
                encoding="utf-8",
            )
            fake_path.chmod(fake_path.stat().st_mode | stat.S_IXUSR)
            candidate = workspace / "main.py"
            inspection = inspect_repository(workspace)

            result = run_agent_execution(
                workspace_root=workspace,
                original_root=original,
                candidate_paths=[candidate],
                inspection=inspection,
                selected_tools=["degrade_naming"],
                profile="maximum",
                intensity="high",
                budget=1,
                dry_run=False,
                provider=CodxProvider(
                    command=os.fspath(fake_path), yolo=False, timeout=30
                ),
                mode="agent",
                allow_rewrites=True,
                max_agent_steps=4,
                max_read_chars=24_000,
                instruction=None,
                artifact_root=root / "artifacts",
            )

            assert result.agent is not None
            self.assertEqual(result.agent.model_calls, 1, msg=str(result.warnings))
            self.assertEqual(
                [action.tool for action in result.agent.actions], ["degrade_naming"]
            )
            self.assertEqual(result.changed_files, ["main.py"])
            self.assertEqual(result.agent.usage.total_tokens, 5)
            self.assertNotEqual(candidate.read_text(encoding="utf-8"), source)
            self.assertEqual((original / "main.py").read_text(encoding="utf-8"), source)


if __name__ == "__main__":
    unittest.main()
