from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from enshittify_tools.agent.mcp_server import StdioMcpSession


class McpServerTests(unittest.TestCase):
    def _session(self, root: Path) -> tuple[StdioMcpSession, Path]:
        original = root / "original"
        workspace = root / "workspace"
        original.mkdir()
        workspace.mkdir()
        source = "def calculate_total(readable_value):\n    return readable_value\n"
        (original / "main.py").write_text(source, encoding="utf-8")
        (workspace / "main.py").write_text(source, encoding="utf-8")
        state_path = root / "state.json"
        return (
            StdioMcpSession(
                {
                    "workspace_root": str(workspace),
                    "original_root": str(original),
                    "candidate_paths": ["main.py"],
                    "inspection": {"python_files": 1},
                    "allowed_mutations": ["degrade_naming"],
                    "mutation_descriptions": {
                        "degrade_naming": "Replace clear names with vague names."
                    },
                    "profile": "maximum",
                    "intensity": "high",
                    "budget": 2,
                    "state_path": str(state_path),
                }
            ),
            state_path,
        )

    @staticmethod
    def _text(response: dict[str, object]) -> dict[str, object]:
        result = response["result"]
        assert isinstance(result, dict)
        content = result["content"]
        assert isinstance(content, list)
        item = content[0]
        assert isinstance(item, dict)
        return json.loads(item["text"])

    def test_mcp_handshake_lists_tools_and_records_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            session, state_path = self._session(Path(temporary))

            initialized = session.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05"},
                }
            )
            assert initialized is not None
            self.assertEqual(initialized["result"]["serverInfo"]["name"], "enshittify")

            listed = session.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            assert listed is not None
            names = [tool["name"] for tool in listed["result"]["tools"]]
            self.assertEqual(
                names,
                [
                    "inspect_workspace",
                    "read_source",
                    "apply_mutation",
                    "rewrite_source",
                    "review_diff",
                ],
            )

            inspected = session.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "inspect_workspace", "arguments": {}},
                }
            )
            assert inspected is not None
            inspection = self._text(inspected)
            self.assertEqual(inspection["budget"]["remaining"], 2)

            mutated = session.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "apply_mutation",
                        "arguments": {
                            "path": "main.py",
                            "mutation": "degrade_naming",
                            "rationale": "Make the example less readable.",
                        },
                    },
                }
            )
            assert mutated is not None
            result = self._text(mutated)
            self.assertTrue(result["ok"])
            self.assertEqual(result["action"]["tool"], "degrade_naming")
            self.assertNotEqual(
                (Path(temporary) / "workspace" / "main.py").read_text(),
                (Path(temporary) / "original" / "main.py").read_text(),
            )
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(len(persisted["actions"]), 1)
            self.assertEqual(persisted["remaining_budget"], 1)

    def test_notifications_are_not_written_as_responses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            session, _ = self._session(Path(temporary))
            self.assertIsNone(
                session.handle(
                    {
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized",
                    }
                )
            )


if __name__ == "__main__":
    unittest.main()
