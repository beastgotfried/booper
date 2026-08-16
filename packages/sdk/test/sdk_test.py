from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

from enshittify_sdk import Enshittify


class SdkTests(unittest.TestCase):
    def test_sdk_writes_isolated_mutation_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            original = '"""Docs."""\ndef f(readable_value: int) -> int:\n    return readable_value\n'
            (source / "main.py").write_text(original, encoding="utf-8")

            result = Enshittify(output_root=root / "runs").run_repository(
                str(source), profile="obfuscation-heavy", intensity="maximum"
            )

            mutated = (result.workspace_dir / "main.py").read_text(encoding="utf-8")
            self.assertEqual((source / "main.py").read_text(encoding="utf-8"), original)
            self.assertNotEqual(mutated, original)
            ast.parse(mutated)
            self.assertTrue(result.patch_path.exists())
            report = json.loads(result.report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["changed_files"], ["main.py"])

    def test_dry_run_consumes_budget_without_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            original = "def f(value):\n    return value\n"
            (source / "main.py").write_text(original, encoding="utf-8")
            result = Enshittify(output_root=root / "runs").run_repository(
                str(source), dry_run=True, budget=2
            )
            self.assertEqual(result.status, "dry_run")
            self.assertEqual((result.workspace_dir / "main.py").read_text(), original)
            self.assertEqual(result.report["summary"]["planned_tool_invocations"], 2)


if __name__ == "__main__":
    unittest.main()
