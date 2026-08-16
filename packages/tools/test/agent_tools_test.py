from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from enshittify_tools.agent import AgentWorkspaceSession


class AgentWorkspaceToolTests(unittest.TestCase):
    def _session(self, root: Path, *, dry_run: bool = False) -> AgentWorkspaceSession:
        original = root / "original"
        workspace = root / "workspace"
        original.mkdir()
        workspace.mkdir()
        code = "def f(readable_value):\n    return readable_value\n"
        (original / "main.py").write_text(code, encoding="utf-8")
        (workspace / "main.py").write_text(code, encoding="utf-8")
        return AgentWorkspaceSession(
            workspace_root=workspace,
            original_root=original,
            candidate_paths=[workspace / "main.py"],
            inspection={"languages": {"Python": 1}},
            allowed_mutations=("degrade_naming",),
            mutation_descriptions={"degrade_naming": "Use vague identifiers."},
            profile="maximum",
            intensity="high",
            budget=2,
            dry_run=dry_run,
        )

    def test_paths_are_restricted_to_exact_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            session = self._session(Path(temporary))
            response = json.loads(session.read_source("../outside.py"))
            self.assertFalse(response["ok"])
            self.assertEqual(session.actions, [])

    def test_invalid_rewrite_is_rejected_and_receipted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            session = self._session(Path(temporary))
            before = (session.workspace_root / "main.py").read_text()
            response = json.loads(
                session.rewrite_source(
                    "main.py", "def broken(:\n", "Break readability."
                )
            )
            self.assertFalse(response["ok"])
            self.assertEqual(session.actions[0].status, "rejected")
            self.assertEqual((session.workspace_root / "main.py").read_text(), before)
            self.assertEqual(session.remaining_budget, 1)

    def test_dry_run_records_a_plan_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            session = self._session(Path(temporary), dry_run=True)
            before = (session.workspace_root / "main.py").read_text()
            response = json.loads(
                session.apply_mutation("main.py", "degrade_naming", "Worsen names.")
            )
            self.assertTrue(response["ok"])
            self.assertEqual(session.actions[0].status, "planned")
            self.assertEqual((session.workspace_root / "main.py").read_text(), before)


if __name__ == "__main__":
    unittest.main()
