from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path


class BasicEndToEndTests(unittest.TestCase):
    def test_dry_run_plans_without_touching_the_source_or_workspace(self) -> None:
        from enshittify_sdk import Enshittify

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            original = "def f(value):\n    return value\n"
            (source / "main.py").write_text(original, encoding="utf-8")

            result = Enshittify(output_root=root / "runs").run_repository(
                str(source),
                tools=["degrade_naming", "inject_dead_code"],
                budget=1,
                dry_run=True,
            )

            workspace_code = (result.workspace_dir / "main.py").read_text(
                encoding="utf-8"
            )
            self.assertEqual(result.status, "dry_run")
            self.assertEqual(workspace_code, original)
            self.assertEqual(result.report["summary"]["planned_tool_invocations"], 1)
            ast.parse(workspace_code)


if __name__ == "__main__":
    unittest.main()
