from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path


class RepositoryHarnessIntegrationTests(unittest.TestCase):
    def test_run_preserves_source_and_writes_reproducible_receipts(self) -> None:
        from enshittify_sdk import Enshittify

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            original = (
                '"""A readable example."""\n'
                "def calculate_total(value):\n"
                "    return value\n"
            )
            (source / "main.py").write_text(original, encoding="utf-8")

            result = Enshittify(output_root=root / "runs").run_repository(
                str(source),
                tools=["degrade_naming", "inject_dead_code"],
                output="archive",
            )

            mutated = (result.workspace_dir / "main.py").read_text(encoding="utf-8")
            self.assertEqual((source / "main.py").read_text(encoding="utf-8"), original)
            self.assertNotEqual(mutated, original)
            ast.parse(mutated)
            self.assertIsNotNone(result.archive_path)
            self.assertTrue(result.archive_path.is_file())

            report = json.loads(result.report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["changed_files"], ["main.py"])
            self.assertEqual(
                report["configuration"]["tools"],
                [
                    "degrade_naming",
                    "inject_dead_code",
                ],
            )
            events = result.run_dir.joinpath("artifacts", "events.jsonl").read_text()
            self.assertIn('"type": "run_completed"', events)


if __name__ == "__main__":
    unittest.main()
